from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.domain.intelligence import Anomaly, OptimizationScenario, Recommendation
from app.domain.structure import Asset, Building, Meter, Zone

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    like = f"%{q}%"
    results = []

    for b in db.query(Building).filter(Building.name.ilike(like)).all():
        results.append({"type": "building", "id": b.id, "label": b.name})
    for z in db.query(Zone).filter(Zone.name.ilike(like)).all():
        results.append({"type": "zone", "id": z.id, "label": z.name})
    for a in db.query(Asset).filter(Asset.name.ilike(like)).all():
        results.append({"type": "asset", "id": a.id, "label": a.name})
    for m in db.query(Meter).filter(Meter.id.ilike(like)).all():
        results.append({"type": "meter", "id": m.id, "label": m.id})
    for an in db.query(Anomaly).filter(Anomaly.probable_cause.ilike(like)).limit(20).all():
        results.append({"type": "anomaly", "id": an.id, "label": f"{an.severity} anomaly on {an.meter_id}"})
    for r in db.query(Recommendation).filter(Recommendation.title.ilike(like)).all():
        results.append({"type": "recommendation", "id": r.id, "label": r.title})
    for s in db.query(OptimizationScenario).filter(OptimizationScenario.name.ilike(like)).all():
        results.append({"type": "scenario", "id": s.id, "label": s.name})

    total = len(results)
    start = (page - 1) * page_size
    page_items = results[start : start + page_size]
    return {"query": q, "page": page, "page_size": page_size, "total": total, "results": page_items}
