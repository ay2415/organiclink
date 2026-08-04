"""
Phase 2 — Two-Stage Bulk Produce Grading Engine for OrganicLink.

Pipeline Order: DETECT -> RECOGNIZE+MATCH -> GRADE -> AGGREGATE -> RIPENESS.
"""

import os
import cv2
from collections import Counter
from cv.detection import detect_items
from cv.inference import get_inference_engine, PRODUCT_SYNONYMS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_DIR = os.path.join(BASE_DIR, "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)
BULK_ANNOTATED_PATH = os.path.join(DEBUG_DIR, "bulk_grading_annotated.jpg")


def compute_iou(box1: list, box2: list) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    if inter_area == 0:
        return 0.0
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    return inter_area / float(box1_area + box2_area - inter_area)


def filter_overlapping_boxes(detections: list, iou_threshold: float = 0.5) -> list:
    if not detections:
        return []
    sorted_dets = sorted(detections, key=lambda d: d.get("confidence", 0.0), reverse=True)
    kept = []
    for d in sorted_dets:
        box = d["bbox"]
        overlap = False
        for k in kept:
            if compute_iou(box, k["bbox"]) > iou_threshold:
                overlap = True
                break
        if not overlap:
            kept.append(d)
    return kept


def grade_bulk(
    image_path: str,
    expected_product: str,
    crop_shrink_factor: float = 0.75,
    det_conf_threshold: float = 0.75
) -> dict:
    if not os.path.exists(image_path):
        return {"status": "error", "message": f"File not found: {image_path}"}

    img = cv2.imread(image_path)
    if img is None:
        return {"status": "error", "message": "Failed to load image."}

    h, w, _ = img.shape
    engine = get_inference_engine()

    raw_detections = detect_items(image_path, conf_threshold=det_conf_threshold)
    all_detections = filter_overlapping_boxes(raw_detections, iou_threshold=0.5)

    synonyms = PRODUCT_SYNONYMS.get(expected_product.lower(), [expected_product.lower()])

    if not all_detections:
        all_detections = [{"box": [0, 0, w, h], "confidence": 1.0, "label": expected_product.lower()}]

    annotated_img = img.copy()
    matching_crops = []
    excluded_crops = []
    skipped_count = 0

    for idx, det in enumerate(all_detections):
        x1, y1, x2, y2 = det["bbox"]

        bw = x2 - x1
        bh = y2 - y1
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0

        sw = max(10, int(bw * crop_shrink_factor))
        sh = max(10, int(bh * crop_shrink_factor))

        sx1 = max(0, int(cx - sw / 2.0))
        sy1 = max(0, int(cy - sh / 2.0))
        sx2 = min(w, int(cx + sw / 2.0))
        sy2 = min(h, int(cy + sh / 2.0))

        crop = img[sy1:sy2, sx1:sx2]
        if crop.size == 0:
            crop = img[y1:y2, x1:x2]
            if crop.size == 0:
                continue

        temp_crop_path = os.path.join(DEBUG_DIR, f"crop_{idx}.jpg")
        cv2.imwrite(temp_crop_path, crop)

        cv_res = engine.analyze_image(temp_crop_path, expected_product=expected_product, skip_mismatch=True)
        if os.path.exists(temp_crop_path):
            os.remove(temp_crop_path)

        pred_prod = cv_res.get("predicted_label", cv_res.get("predicted_product", "")).lower()
        prod_conf = cv_res.get("neural_confidence", cv_res.get("product_confidence", 0.0))
        cv_status = cv_res.get("status", "graded")

        raw_score = cv_res.get("quality_score")
        condition = cv_res.get("predicted_condition", cv_res.get("condition"))
        quality_grade = cv_res.get("quality_grade")

        # In bulk mode, do not reject individual crops based on per-crop product guesses.
        # Include every crop with valid quality output.
        exclude_reason = None
        if cv_status in ["unclear_image", "not_gradable", "unavailable"]:
            exclude_reason = f"cv_status_{cv_status}"
        elif raw_score is None:
            exclude_reason = "missing_quality_score"

        included = (exclude_reason is None)
        weight_used = det.get("confidence", 1.0) if included else 0.0

        is_match = (pred_prod in synonyms) or (expected_product.lower() in pred_prod)

        print(f"[DEBUG item #{idx+1}] yolo_class={det.get('class_name', expected_product)}, "
              f"yolo_conf={det.get('confidence', 1.0):.4f}, pred_prod={pred_prod}, "
              f"prod_conf={prod_conf:.2f}, expected={expected_product}, "
              f"cv_status={cv_status}, quality_score={raw_score}, included={'yes' if included else 'no'}"
              + (f" (reason: {exclude_reason})" if exclude_reason else ""))

        det_entry = {
            "index": idx + 1,
            "bbox": [x1, y1, x2, y2],
            "pred_product": pred_prod,
            "product_conf": prod_conf,
            "is_match": is_match,
            "condition": condition if condition else "fresh",
            "quality_score": raw_score if raw_score is not None else 85.0,
            "quality_grade": quality_grade if quality_grade else "A",
            "probs": cv_res.get("cv_breakdown", {}).get("class_probabilities", {}),
            "ripeness": cv_res.get("cv_breakdown", {}).get("ripeness"),
            "included": included,
            "exclude_reason": exclude_reason,
            "weight": weight_used
        }

        if included:
            matching_crops.append(det_entry)
        else:
            excluded_crops.append(det_entry)

    total_detected = len(all_detections)
    matching_total = len(matching_crops)

    # --- BATCH-LEVEL MISMATCH CHECK (Top 5 Highest-Detection-Confidence Crops) ---
    sorted_all_crops = sorted(matching_crops + excluded_crops, key=lambda c: c["weight"], reverse=True)
    top_5_crops = sorted_all_crops[:5]
    disagree_crops = [c for c in top_5_crops if not c["is_match"] and c["product_conf"] >= 60.0]

    has_batch_mismatch_warning = False
    if len(top_5_crops) >= 3 and len(disagree_crops) >= (len(top_5_crops) / 2.0):
        has_batch_mismatch_warning = True
        most_common_found = Counter(c["pred_product"] for c in disagree_crops).most_common(1)[0][0]
        print(f"[Bulk Grading Warning] Possible product mismatch detected: Majority of top crops look like {most_common_found.title()}, expected {expected_product.title()}.")

    fresh_count = 0
    minor_count = 0
    major_count = 0
    weighted_score_sum = 0.0
    weight_sum = 0.0
    defective_items = []
    item_results = []
    ripeness_labels = []

    for item in matching_crops:
        cond = item["condition"]
        score = item["quality_score"]
        weight = item["weight"]
        box = item["bbox"]
        x1, y1, x2, y2 = box

        if cond == "fresh":
            fresh_count += 1
            color = (0, 220, 0)
        elif cond == "minor_defect":
            minor_count += 1
            color = (0, 200, 255)
            defective_items.append({"item": item["index"], "condition": "minor_defect", "score": score})
        else:
            major_count += 1
            color = (0, 0, 255)
            defective_items.append({"item": item["index"], "condition": "major_defect", "score": score})

        weighted_score_sum += score * weight
        weight_sum += weight

        item_results.append({
            "item_number": item["index"],
            "condition": cond,
            "quality_score": score,
            "quality_grade": item["quality_grade"]
        })

        if item.get("ripeness"):
            ripeness_labels.append(item["ripeness"])

        cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(annotated_img, f"#{item['index']} {cond.upper()} ({score:.0f})", (x1, max(15, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    for item in excluded_crops:
        x1, y1, x2, y2 = item["bbox"]
        cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (255, 0, 255), 2)
        cv2.putText(annotated_img, f"EXCLUDED: {item['pred_product']}", (x1, max(15, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

    fresh_percent = round((fresh_count / float(matching_total)) * 100.0, 1)
    defect_percent = round(((minor_count + major_count) / float(matching_total)) * 100.0, 1)

    final_score = round(weighted_score_sum / weight_sum, 1) if weight_sum > 0 else 0.0

    if final_score >= 88.0 and fresh_percent >= 80.0:
        batch_grade = "A"
    elif final_score >= 72.0 and fresh_percent >= 60.0:
        batch_grade = "B"
    elif final_score >= 50.0 and fresh_percent >= 50.0:
        batch_grade = "C"
    else:
        batch_grade = "R"

    excluded_reasons = Counter([it["exclude_reason"] for it in excluded_crops])
    print(f"[SUMMARY DEBUG] total_items_detected={total_detected}, items_included={matching_total}, "
          f"items_excluded_reasons={dict(excluded_reasons)}, weighted_score_sum={weighted_score_sum:.2f}, "
          f"weight_sum={weight_sum:.2f}, final_score={final_score}, final_grade={batch_grade}")

    ripeness_note = None
    if expected_product.lower() == "tomato" and ripeness_labels:
        counts = Counter(ripeness_labels)
        ripeness_note = "Ripeness: " + ", ".join(f"{count} {r}" for r, count in counts.items())

    os.makedirs(os.path.dirname(BULK_ANNOTATED_PATH), exist_ok=True)
    cv2.imwrite(BULK_ANNOTATED_PATH, annotated_img)

    excl_msg = f" ({len(excluded_crops)} item excluded)" if excluded_crops else ""
    message = f"Bulk Inspection Complete: {fresh_count} of {matching_total} {expected_product}s fresh ({fresh_percent}%). Batch Grade {batch_grade}. Weighted Score: {final_score}/100.{excl_msg}"

    batch_result = {
        "status": "graded",
        "product_mismatch": False,
        "is_bulk": True,
        "total_items_detected": len(all_detections),
        "matching_items_total": matching_total,
        "excluded_items_count": len(excluded_crops),
        "skipped_low_conf_count": skipped_count,
        "fresh_count": fresh_count,
        "minor_defect_count": minor_count,
        "major_defect_count": major_count,
        "fresh_percent": fresh_percent,
        "defect_percent": defect_percent,
        "weighted_quality_score": final_score,
        "batch_grade": batch_grade,
        "ripeness_note": ripeness_note,
        "defective_items": defective_items,
        "item_results": item_results,
        "annotated_image_path": BULK_ANNOTATED_PATH,
        "message": message
    }

    print(f"[Bulk Grading] {message}")
    return batch_result
