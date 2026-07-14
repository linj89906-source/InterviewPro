import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.database import SessionLocal, engine, Base
from app.services.knowledge_base import KnowledgeDoc, init_fts

Base.metadata.create_all(bind=engine)
init_fts()

SEED_DATA = json.load(open(os.path.join(os.path.dirname(__file__), "seed_data.json"), "r", encoding="utf-8"))

def seed():
    db = SessionLocal()
    try:
        existing = db.query(KnowledgeDoc).count()
        if existing > 0:
            print(f"[SKIP] Knowledge base has {existing} records")
            return
        for doc in SEED_DATA:
            db.add(KnowledgeDoc(**doc))
        db.commit()
        print(f"[OK] Inserted {len(SEED_DATA)} docs")
        for cat in ["Java", "Python", "\u7b97\u6cd5", "\u6570\u636e\u5e93", "\u7f51\u7edc"]:
            cnt = db.query(KnowledgeDoc).filter(KnowledgeDoc.category == cat).count()
            print(f"  {cat}: {cnt}")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()