"""
Quality Inspections & Certificates router for OrganicLink.
"""

import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User, QualityInspection, Product, Farm
from schemas.schemas import QualityInspectionResponse
from routers.auth import get_current_user
from cv.inference import get_inference_engine
from services.documents import UPLOADS_DIR, PDF_DIR, generate_quality_certificate_pdf

router = APIRouter(prefix="/api/quality", tags=["Quality"])


@router.post("/analyze")
def analyze_image_quality(
    image: UploadFile = File(...),
    product_id: str = Form(None),
    product_type: str = Form("unknown"),
    inspection_level: str = Form("farm"), # farm, delivery
    is_bulk: Optional[str] = Form("false"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(image.filename)[1] or ".jpg"
    filename = f"insp_{uuid.uuid4().hex}{ext}"
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image.file.read())

    image_url = f"/static/uploads/{filename}"
    is_bulk_flag = str(is_bulk).lower() in ["true", "1", "yes"]

    if is_bulk_flag:
        from cv.bulk_grading import grade_bulk
        batch_res = grade_bulk(filepath, expected_product=product_type)
        if batch_res.get("status") == "mismatch" or batch_res.get("product_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=batch_res.get("message", f"Product Mismatch: This photo does not look like {product_type}.")
            )
        else:
            score = batch_res.get("weighted_quality_score", 70.0)
            grade = batch_res.get("batch_grade", "C")
            bulk_summary = f"{batch_res.get('fresh_count', 0)} of {batch_res.get('matching_items_total', 1)} items fresh"
            
            # Copy annotated image so the preview displays the annotated image with bounding boxes
            import shutil
            ann_path = batch_res.get("annotated_image_path", "")
            if ann_path and os.path.exists(ann_path):
                annotated_filename = f"bulk_insp_{uuid.uuid4().hex}.jpg"
                annotated_filepath = os.path.join(UPLOADS_DIR, annotated_filename)
                shutil.copy(ann_path, annotated_filepath)
                image_url = f"/static/uploads/{annotated_filename}"

            res = {
                "quality_score": score,
                "quality_grade": grade,
                "cv_breakdown": {
                    "is_bulk": True,
                    "batch_summary": bulk_summary,
                    "total_items": batch_res.get('total_items_detected', 1),
                    "matching_items": batch_res.get('matching_items_total', 1),
                    "excluded_items": batch_res.get('excluded_items_count', 0),
                    "fresh_count": batch_res.get('fresh_count', 0),
                    "fresh_percent": batch_res.get('fresh_percent', 0.0),
                    "defect_percent": batch_res.get('defect_percent', 0.0),
                    "weighted_score": score,
                    "ripeness_note": batch_res.get('ripeness_note'),
                    "item_results": batch_res.get('item_results', []),
                    "defective_items": batch_res.get('defective_items', [])
                }
            }
    else:
        engine = get_inference_engine()
        res = engine.analyze_image(filepath, expected_product=product_type)

    inspection = QualityInspection(
        product_id=product_id,
        inspection_level=inspection_level,
        image_url=image_url,
        cv_results=res.get("cv_breakdown", {}),
        quality_score=res.get("quality_score", 0.0),
        quality_grade=res.get("quality_grade", "R"),
        defects_detected=res.get("cv_breakdown", {}).get("detected_defects", []),
        model_confidence=0.0,
        model_version="1.1",
        inspector_id=current_user.id
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    return {
        "inspection_id": inspection.id,
        "image_url": image_url,
        "analysis": res
    }


@router.get("/{inspection_id}")
def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.query(QualityInspection).filter(QualityInspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Quality inspection record not found")
    return insp


@router.get("/{inspection_id}/certificate")
def download_certificate(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.query(QualityInspection).filter(QualityInspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Quality inspection record not found")

    filename = f"cert_{inspection_id[:8]}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    if not os.path.exists(filepath):
        # Generate on the fly
        product = db.query(Product).filter(Product.id == insp.product_id).first() if insp.product_id else None
        farm = db.query(Farm).filter(Farm.id == product.farm_id).first() if product else None
        generate_quality_certificate_pdf(
            inspection_data={
                "id": insp.id,
                "inspection_level": insp.inspection_level,
                "quality_score": insp.quality_score,
                "quality_grade": insp.quality_grade,
                "cv_results": insp.cv_results,
                "defects_detected": insp.defects_detected,
                "model_confidence": insp.model_confidence,
                "model_version": insp.model_version,
                "created_at": insp.created_at
            },
            farm_name=farm.farm_name if farm else "Irish Organic Farm",
            product_name=product.product_type if product else "Produce"
        )

    return FileResponse(filepath, media_type="application/pdf", filename=filename)
