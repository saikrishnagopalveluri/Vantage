from app.models import Capability, Company, CompanyRoleCapability, Role, RoleCapability, Source, Topic
from app.seed import seed_sources, seed_taxonomy
from app.seed_data.sources import NEWSLETTERS
from app.sync import sync_taxonomy


def test_sync_restores_missing_curated_data_and_is_idempotent(db):
    seed_taxonomy(db)
    role = db.query(Role).filter_by(title="Retail AI Team Lead").one()
    db.query(RoleCapability).filter_by(role_id=role.id).delete()
    db.query(CompanyRoleCapability).filter_by(role_id=role.id).delete()
    db.delete(role)
    db.query(Topic).filter_by(name="Direct-to-Consumer Brands").delete()
    db.commit()

    first = sync_taxonomy(db)
    assert first["roles"] == 1 and first["topics"] == 1 and first["links"] > 0
    restored = db.query(Role).filter_by(title="Retail AI Team Lead").one()
    assert restored.taggable and db.query(RoleCapability).filter_by(role_id=restored.id).count() >= 5
    assert sync_taxonomy(db) == {k: 0 for k in first}


def test_sync_refreshes_blockers_on_an_already_curated_capability(db):
    """A data correction (a false-positive tag found in production) must reach a capability that
    was curated from day one, not just one being promoted from an imported source."""
    seed_taxonomy(db)
    excel = db.query(Capability).filter_by(name="Excel").one()
    assert excel.source == "curated"
    db.query(Capability).filter_by(id=excel.id).update({"blockers": []})
    db.commit()

    sync_taxonomy(db)
    assert db.query(Capability).filter_by(name="Excel").one().blockers == ["Surf Excel"]


def test_seed_sources_refreshes_feed_url_and_authority_for_an_existing_source(db):
    """A data correction (a source re-ranked, or its feed URL moved) must reach a source already
    in the database, not just add sources that are missing entirely."""
    seed_sources(db)
    name, url, authority = NEWSLETTERS[-1]
    db.query(Source).filter_by(name=name).update({"feed_url": "https://stale.example/feed", "authority": 1})
    db.commit()

    seed_sources(db)
    refreshed = db.query(Source).filter_by(name=name).one()
    assert refreshed.feed_url == url and refreshed.authority == authority


def test_sync_promotes_an_imported_name_instead_of_duplicating_it(db):
    seed_taxonomy(db)
    curated = db.query(Company).filter_by(name="Farfetch").one()
    db.query(Company).filter_by(id=curated.id).update({"source": "sec", "taggable": False, "industry_id": None})
    db.query(Capability).filter_by(name="Cybersecurity").update({"source": "onet", "taggable": False})
    db.commit()

    stats = sync_taxonomy(db)
    assert stats["promoted"] >= 1
    farfetch = db.query(Company).filter_by(name="Farfetch").one()
    assert farfetch.source == "curated" and farfetch.taggable and farfetch.industry_id
    assert db.query(Capability).filter_by(name="Cybersecurity").one().source == "curated"
    assert db.query(Company).filter(Company.name.like("Farfetch%")).count() == 1


def test_handout_placement_roles_carry_the_companys_own_skill_list(db):
    seed_taxonomy(db)
    role = db.query(Role).filter_by(title="Risk Advisory Analyst, Digital Transformation and Cybersecurity").one()
    deloitte = db.query(Company).filter_by(name="Deloitte").one()
    skills = {
        c.name
        for c in db.query(Capability).join(CompanyRoleCapability, CompanyRoleCapability.capability_id == Capability.id)
        .filter(CompanyRoleCapability.company_id == deloitte.id, CompanyRoleCapability.role_id == role.id)
    }
    assert {"Threat Analysis", "Data Security", "Digital Framework Evaluation", "Cybersecurity"} <= skills
