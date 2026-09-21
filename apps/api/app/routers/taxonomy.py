"""Reference data and the Explore views. Public: nothing here is user-specific."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.deps import get_db
from app.feed import SearchHit, article_hits, search_articles
from app.hiring import companies_hiring_domain, companies_hiring_role, roles_hired_by
from app.models import (
    Article,
    ArticleTag,
    Capability,
    CapabilityKind,
    Company,
    Domain,
    Industry,
    Role,
    RoleCapability,
    TagType,
)
from app.search_terms import variants
from app.schemas import (
    ArticleBrief,
    CapabilityRef,
    CompanyDetail,
    CompanyOut,
    DomainOut,
    DomainRoles,
    NamedRef,
    RelatedRole,
    RoleDetail,
    RoleRef,
    SearchOut,
    SourceRef,
)
from app.services import capability_ref, domain_ref, role_ref

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])

Limit = Query(default=100, ge=1, le=500)
Offset = Query(default=0, ge=0)
RELATED_ROLES = 6
MIN_SIMILARITY = 0.12
COMPANIES_SHOWN = 24
ROLES_PER_FIELD = 12
VARIANTS_SHOWN = 12


def _company_out(c: Company) -> CompanyOut:
    return CompanyOut(
        id=c.id, name=c.name, mba=c.mba, industry=NamedRef(id=c.industry.id, name=c.industry.name) if c.industry else None
    )


def _brief(hit: SearchHit) -> ArticleBrief:
    a = hit.article
    return ArticleBrief(
        id=a.id,
        title=a.title,
        url=a.url,
        summary=a.summary,
        source=SourceRef(name=a.source.name, authority=a.source.authority),
        published_at=hit.published,
        tags=hit.tags,
    )


def _match(column, q: str):
    """Contains the query or one of its other spellings and expansions (modelling, DCF, MS Excel)."""
    return or_(*(column.icontains(v, autoescape=True) for v in variants(q)))


def _relevance(column, q: str | None, boost=None):
    """Order matches so a prefix beats a mid-word hit, then what management students want first,
    then shorter (more specific) names."""
    first = [boost.desc()] if boost is not None else []
    if not q:
        return [*first, column]
    starts = or_(*(func.lower(column).like(f"{v}%") for v in variants(q)))
    return [
        case((starts, 0), else_=1),
        *first,
        func.length(column),
        column,
    ]


@router.get("/domains", response_model=list[DomainOut])
def domains(db: Session = Depends(get_db)):
    titles = dict(db.execute(select(Role.domain_id, func.count(Role.id)).group_by(Role.domain_id)).all())
    families = dict(
        db.execute(select(Role.domain_id, func.count(Role.id)).where(Role.parent_id.is_(None)).group_by(Role.domain_id)).all()
    )
    return [
        DomainOut(
            id=d.id,
            name=d.name,
            slug=d.slug,
            group=d.group,
            role_count=titles.get(d.id, 0),
            family_count=families.get(d.id, 0),
        )
        for d in db.scalars(select(Domain).order_by(Domain.name))
    ]


@router.get("/roles", response_model=list[RoleRef])
def roles(
    q: str | None = None,
    domain_id: str | None = None,
    families_only: bool = False,
    mba: bool = False,
    limit: int = Limit,
    offset: int = Offset,
    db: Session = Depends(get_db),
):
    """Curated roles and role families first, then the long tail of title variants."""
    stmt = select(Role).options(selectinload(Role.domain), selectinload(Role.parent))
    if q:
        stmt = stmt.where(_match(Role.title, q))
    if domain_id:
        stmt = stmt.where(Role.domain_id == domain_id)
    if families_only:
        stmt = stmt.where(Role.parent_id.is_(None))
    if mba:
        stmt = stmt.where(Role.mba.is_(True))
    stmt = stmt.order_by(case((Role.parent_id.is_(None), 0), else_=1), *_relevance(Role.title, q, Role.mba)).limit(limit).offset(offset)
    return [role_ref(r) for r in db.scalars(stmt)]


@router.get("/roles/{role_id}", response_model=RoleDetail)
def role_detail(role_id: str, db: Session = Depends(get_db)):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    base = role.parent if role.parent_id else role

    caps = list(
        db.scalars(
            select(Capability)
            .join(RoleCapability, RoleCapability.capability_id == Capability.id)
            .where(RoleCapability.role_id == base.id)
            .options(selectinload(Capability.domain))
            .order_by(Capability.kind, Capability.name)
        )
    )
    hiring = companies_hiring_role(db, role)
    companies_total = db.scalar(select(func.count()).select_from(hiring.subquery())) or 0
    companies = list(
        db.scalars(
            hiring.options(selectinload(Company.industry))
            .order_by(case((Company.source == "curated", 0), else_=1), Company.name)
            .limit(COMPANIES_SHOWN)
        )
    )

    # Adjacent roles: the families asking for the most similar set of skills, found in SQL
    # because comparing against every role in Python would not scale to thousands.
    own = {c.id for c in caps}
    related: list[RelatedRole] = []
    if own:
        shared_counts = db.execute(
            select(RoleCapability.role_id, func.count().label("shared"))
            .where(RoleCapability.capability_id.in_(own), RoleCapability.role_id != base.id)
            .group_by(RoleCapability.role_id)
            .order_by(func.count().desc())
            .limit(40)
        ).all()
        candidate_ids = [r for r, _ in shared_counts]
        totals = dict(
            db.execute(
                select(RoleCapability.role_id, func.count()).where(RoleCapability.role_id.in_(candidate_ids)).group_by(RoleCapability.role_id)
            ).all()
        )
        scored = sorted(
            (
                (shared / (len(own) + totals[rid] - shared), rid, shared)
                for rid, shared in shared_counts
                if len(own) + totals[rid] - shared
            ),
            key=lambda item: (-item[0], item[1]),
        )
        scored = [item for item in scored if item[0] >= MIN_SIMILARITY][:RELATED_ROLES]
        others = {
            r.id: r
            for r in db.scalars(
                select(Role).where(Role.id.in_([i for _, i, _ in scored])).options(selectinload(Role.domain), selectinload(Role.parent))
            )
        }
        names = {c.id: c.name for c in caps}
        overlaps = defaultdict(list)
        for cap_id, other_role in db.execute(
            select(RoleCapability.capability_id, RoleCapability.role_id).where(
                RoleCapability.role_id.in_([i for _, i, _ in scored]), RoleCapability.capability_id.in_(own)
            )
        ):
            overlaps[other_role].append(names[cap_id])
        related = [
            RelatedRole(role=role_ref(others[rid]), shared_capabilities=sorted(overlaps[rid]), similarity=round(sim, 2))
            for sim, rid, _ in scored
        ]

    variants = [] if role.parent_id else [
        t for t in db.scalars(select(Role.title).where(Role.parent_id == role.id).order_by(func.length(Role.title), Role.title).limit(VARIANTS_SHOWN))
    ]
    return RoleDetail(
        id=role.id,
        title=role.title,
        domain=domain_ref(role.domain or base.domain),
        description=base.description,
        canonical=NamedRef(id=base.id, name=base.title) if role.parent_id else None,
        aliases=list(role.aliases or []),
        variants=variants,
        capabilities=[capability_ref(c) for c in caps],
        companies=[_company_out(c) for c in companies],
        companies_total=companies_total,
        related_roles=related,
    )


@router.get("/industries", response_model=list[NamedRef])
def industries(q: str | None = None, limit: int = Limit, db: Session = Depends(get_db)):
    stmt = select(Industry).order_by(Industry.name).limit(limit)
    if q:
        stmt = stmt.where(Industry.name.icontains(q, autoescape=True))
    return [NamedRef(id=i.id, name=i.name) for i in db.scalars(stmt)]


@router.get("/companies", response_model=list[CompanyOut])
def companies(
    q: str | None = None,
    industry_id: str | None = None,
    domain_id: str | None = None,
    mba: bool = False,
    limit: int = Limit,
    offset: int = Offset,
    db: Session = Depends(get_db),
):
    """Hand-curated companies first, then everything else by relevance to the search."""
    stmt = select(Company).options(selectinload(Company.industry))
    if domain_id:
        stmt = companies_hiring_domain(domain_id).options(selectinload(Company.industry))
    if q:
        stmt = stmt.where(_match(Company.name, q))
    if industry_id:
        stmt = stmt.where(Company.industry_id == industry_id)
    if mba:
        stmt = stmt.where(Company.mba.is_(True))
    stmt = stmt.order_by(case((Company.source == "curated", 0), else_=1), *_relevance(Company.name, q, Company.mba)).limit(limit).offset(offset)
    return [_company_out(c) for c in db.scalars(stmt)]


@router.get("/companies/{company_id}", response_model=CompanyDetail)
def company_detail(company_id: str, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    hired = list(db.scalars(roles_hired_by(company).options(selectinload(Role.domain)).order_by(Role.title)))
    grouped: dict[str, list[Role]] = defaultdict(list)
    for role in hired:
        grouped[role.domain.name if role.domain else ""].append(role)
    roles_by_domain = [
        DomainRoles(
            domain=domain_ref(items[0].domain),
            roles=[role_ref(r) for r in sorted(items, key=lambda r: (r.source != "curated", r.title))[:ROLES_PER_FIELD]],
            total=len(items),
        )
        for _, items in sorted(grouped.items())
    ]
    articles = list(
        db.scalars(
            select(Article)
            .join(ArticleTag, ArticleTag.article_id == Article.id)
            .where(ArticleTag.tag_type == TagType.COMPANY, ArticleTag.ref_id == company_id)
            .order_by(Article.published_at.desc())
            .limit(8)
        )
    )
    return CompanyDetail(
        id=company.id,
        name=company.name,
        industry=NamedRef(id=company.industry.id, name=company.industry.name) if company.industry else None,
        roles_by_domain=roles_by_domain,
        articles=[_brief(h) for h in article_hits(db, articles)],
    )


@router.get("/capabilities", response_model=list[CapabilityRef])
def capabilities(
    q: str | None = None,
    kind: CapabilityKind | None = None,
    domain_id: str | None = None,
    mba: bool = False,
    limit: int = Limit,
    offset: int = Offset,
    db: Session = Depends(get_db),
):
    stmt = select(Capability).options(selectinload(Capability.domain))
    if q:
        stmt = stmt.where(_match(Capability.name, q))
    if kind:
        stmt = stmt.where(Capability.kind == kind)
    if domain_id:
        # A domain's skills, plus the ones every domain uses (Excel, SQL, ...).
        stmt = stmt.where(or_(Capability.domain_id == domain_id, Capability.domain_id.is_(None)))
    if mba:
        stmt = stmt.where(Capability.mba.is_(True))
    stmt = stmt.order_by(case((Capability.source == "curated", 0), else_=1), *_relevance(Capability.name, q, Capability.mba)).limit(limit).offset(offset)
    return [capability_ref(c) for c in db.scalars(stmt)]


@router.get("/search", response_model=SearchOut)
def search(q: str = Query(min_length=2, max_length=80), db: Session = Depends(get_db)):
    """One box for everything: roles, companies, skills and articles."""
    return SearchOut(
        query=q,
        roles=[
            role_ref(r)
            for r in db.scalars(
                select(Role)
                .where(_match(Role.title, q))
                .options(selectinload(Role.domain), selectinload(Role.parent))
                .order_by(case((Role.parent_id.is_(None), 0), else_=1), *_relevance(Role.title, q))
                .limit(8)
            )
        ],
        companies=[
            _company_out(c)
            for c in db.scalars(
                select(Company)
                .where(_match(Company.name, q))
                .options(selectinload(Company.industry))
                .order_by(case((Company.source == "curated", 0), else_=1), *_relevance(Company.name, q))
                .limit(8)
            )
        ],
        capabilities=[
            capability_ref(c)
            for c in db.scalars(
                select(Capability)
                .where(_match(Capability.name, q))
                .options(selectinload(Capability.domain))
                .order_by(case((Capability.source == "curated", 0), else_=1), *_relevance(Capability.name, q))
                .limit(8)
            )
        ],
        articles=[_brief(h) for h in search_articles(db, q, limit=10)],
    )
