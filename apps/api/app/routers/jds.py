from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.deps import get_caller_id, get_db, require_self
from app.jds import MAX_JDS, extract_skills
from app.models import JD, Capability, Company, JDCapability, Role, UserCapability, UserProfile
from app.schemas import JDGap, JDGapsOut, JDIn, JDOut, JDPatch, JDSkill, NamedRef
from app.services import role_ref

router = APIRouter(prefix="/jds", tags=["job descriptions"])

_GAP_LIMIT = 40


def _own(db: Session, user_id: str, caller_id: str) -> None:
    require_self(user_id, caller_id)
    if db.get(UserProfile, user_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")


def _get(db: Session, user_id: str, jd_id: str) -> JD:
    jd = db.get(JD, jd_id)
    if jd is None or jd.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job description not found")
    return jd


def _check_links(db: Session, company_id: str | None, role_id: str | None) -> None:
    if company_id and db.get(Company, company_id) is None:
        raise HTTPException(status_code=422, detail="That company doesn't exist.")
    if role_id and db.get(Role, role_id) is None:
        raise HTTPException(status_code=422, detail="That role doesn't exist.")


def _skills_by_jd(db: Session, user_id: str, jd_ids: list[str]) -> dict[str, list[JDSkill]]:
    have = set(db.scalars(select(UserCapability.capability_id).where(UserCapability.user_id == user_id)))
    rows = db.execute(
        select(JDCapability.jd_id, Capability)
        .join(Capability, Capability.id == JDCapability.capability_id)
        .where(JDCapability.jd_id.in_(jd_ids))
    ).all()
    out: dict[str, list[JDSkill]] = defaultdict(list)
    for jd_id, cap in rows:
        out[jd_id].append(JDSkill(capability_id=cap.id, name=cap.name, kind=cap.kind, user_has_it=cap.id in have))
    for skills in out.values():
        skills.sort(key=lambda s: (s.user_has_it, s.kind.value != "skill", s.name.lower()))
    return out


def _out(jd: JD, skills: list[JDSkill]) -> JDOut:
    has = sum(s.user_has_it for s in skills)
    return JDOut(
        id=jd.id,
        title=jd.title,
        company=NamedRef(id=jd.company.id, name=jd.company.name) if jd.company else None,
        role=role_ref(jd.role) if jd.role else None,
        company_name=jd.company_name,
        created_at=jd.created_at,
        skills=skills,
        coverage=round(100 * has / len(skills)) if skills else 0,
    )


def _title_from(text: str) -> str:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first if len(first) <= 80 else first[:79].rsplit(" ", 1)[0] + "…"


@router.post("/{user_id}", response_model=JDOut, status_code=201)
def add_jd(
    user_id: str,
    body: JDIn,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> JDOut:
    _own(db, user_id, caller_id)
    if db.scalar(select(func.count()).select_from(JD).where(JD.user_id == user_id)) >= MAX_JDS:
        raise HTTPException(
            status_code=409, detail=f"You can keep up to {MAX_JDS} job descriptions. Remove one to add another."
        )
    _check_links(db, body.company_id, body.role_id)
    found = extract_skills(db, body.text)
    if not found:
        raise HTTPException(
            status_code=422,
            detail="We couldn't find any skills or tools we know in that text. Paste the requirements section and try again.",
        )
    jd = JD(
        user_id=user_id,
        title=(body.title or "").strip() or _title_from(body.text),
        company_id=body.company_id,
        role_id=body.role_id,
        company_name=(body.company_name or "").strip() or None,
        raw_text=body.text,
    )
    db.add(jd)
    db.flush()
    db.add_all(JDCapability(jd_id=jd.id, capability_id=c.id) for c in found)
    db.commit()
    return _out(jd, _skills_by_jd(db, user_id, [jd.id])[jd.id])


@router.get("/{user_id}", response_model=list[JDOut])
def list_jds(
    user_id: str, db: Session = Depends(get_db), caller_id: str = Depends(get_caller_id)
) -> list[JDOut]:
    _own(db, user_id, caller_id)
    jds = list(db.scalars(select(JD).where(JD.user_id == user_id).order_by(JD.created_at.desc())))
    skills = _skills_by_jd(db, user_id, [j.id for j in jds])
    return [_out(j, skills.get(j.id, [])) for j in jds]


@router.get("/{user_id}/gaps", response_model=JDGapsOut)
def jd_gaps(
    user_id: str, db: Session = Depends(get_db), caller_id: str = Depends(get_caller_id)
) -> JDGapsOut:
    """What the saved jobs ask for, most-requested first, with the skills the reader lacks on top."""
    _own(db, user_id, caller_id)
    jd_ids = list(db.scalars(select(JD.id).where(JD.user_id == user_id)))
    skills = _skills_by_jd(db, user_id, jd_ids)
    counts: dict[str, JDGap] = {}
    covered = total = 0
    for jd_id in jd_ids:
        for s in skills.get(jd_id, []):
            total += 1
            covered += s.user_has_it
            gap = counts.setdefault(
                s.capability_id,
                JDGap(
                    capability_id=s.capability_id, name=s.name, kind=s.kind, jd_count=0,
                    jd_total=len(jd_ids), user_has_it=s.user_has_it,
                ),
            )
            gap.jd_count += 1
    ordered = sorted(counts.values(), key=lambda g: (g.user_has_it, -g.jd_count, g.name.lower()))
    return JDGapsOut(
        jd_count=len(jd_ids), coverage=round(100 * covered / total) if total else 0, skills=ordered[:_GAP_LIMIT]
    )


@router.get("/{user_id}/{jd_id}", response_model=JDOut)
def get_jd(
    user_id: str, jd_id: str, db: Session = Depends(get_db), caller_id: str = Depends(get_caller_id)
) -> JDOut:
    _own(db, user_id, caller_id)
    jd = _get(db, user_id, jd_id)
    return _out(jd, _skills_by_jd(db, user_id, [jd.id])[jd.id])


@router.patch("/{user_id}/{jd_id}", response_model=JDOut)
def patch_jd(
    user_id: str,
    jd_id: str,
    body: JDPatch,
    db: Session = Depends(get_db),
    caller_id: str = Depends(get_caller_id),
) -> JDOut:
    _own(db, user_id, caller_id)
    jd = _get(db, user_id, jd_id)
    fields = body.model_dump(exclude_unset=True)
    _check_links(db, fields.get("company_id"), fields.get("role_id"))
    for name, value in fields.items():
        setattr(jd, name, (value.strip() or None) if isinstance(value, str) else value)
    db.commit()
    return _out(jd, _skills_by_jd(db, user_id, [jd.id])[jd.id])


@router.delete("/{user_id}/{jd_id}", status_code=204)
def delete_jd(
    user_id: str, jd_id: str, db: Session = Depends(get_db), caller_id: str = Depends(get_caller_id)
) -> None:
    _own(db, user_id, caller_id)
    jd = _get(db, user_id, jd_id)
    db.execute(delete(JDCapability).where(JDCapability.jd_id == jd.id))
    db.delete(jd)
    db.commit()
