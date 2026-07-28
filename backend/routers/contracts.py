"""
Contracts router for OrganicLink.
Manages fixed farmer contracts with manufacturers/processors.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User, Farm, Contract
from schemas.schemas import ContractCreate, ContractUpdate, ContractResponse
from routers.auth import get_current_user

router = APIRouter(prefix="/api", tags=["Contracts"])


@router.post("/farms/{farm_id}/contracts", response_model=ContractResponse)
def create_contract(
    farm_id: str,
    contract_in: ContractCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm or (farm.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")

    contract = Contract(
        farm_id=farm_id,
        contract_name=contract_in.contract_name,
        hub_name=contract_in.hub_name,
        product_type=contract_in.product_type.lower(),
        committed_quantity=contract_in.committed_quantity,
        quantity_unit=contract_in.quantity_unit.lower(),
        period=contract_in.period,
        price_per_unit=contract_in.price_per_unit,
        collection_schedule=contract_in.collection_schedule,
        status=contract_in.status,
        start_date=contract_in.start_date,
        end_date=contract_in.end_date
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/farms/{farm_id}/contracts", response_model=List[ContractResponse])
def list_farm_contracts(farm_id: str, db: Session = Depends(get_db)):
    from datetime import date
    from models.all_models import ProductionLog
    contracts = db.query(Contract).filter(Contract.farm_id == farm_id, Contract.is_deleted == False).all()
    today = date.today()
    res = []
    for c in contracts:
        c_res = ContractResponse.model_validate(c)
        if c.end_date:
            days_rem = (c.end_date - today).days
            c_res.days_remaining = days_rem
            if days_rem < 0:
                c_res.status = "expired"

        # Compute fulfillment to date against production logs
        logged_sum = db.query(ProductionLog).filter(
            ProductionLog.farm_id == farm_id,
            ProductionLog.product_type == c.product_type
        ).all()
        total_logged = sum(l.quantity for l in logged_sum)
        fulfillment = round(min(100.0, (total_logged / c.committed_quantity) * 100.0), 1) if c.committed_quantity > 0 else 100.0
        c_res.fulfillment_percent = fulfillment

        res.append(c_res)
    return res


@router.put("/contracts/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: str,
    contract_in: ContractUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.is_deleted == False).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    farm = db.query(Farm).filter(Farm.id == contract.farm_id).first()
    if farm.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    if contract_in.contract_name is not None:
        contract.contract_name = contract_in.contract_name
    if contract_in.committed_quantity is not None:
        contract.committed_quantity = contract_in.committed_quantity
    if contract_in.price_per_unit is not None:
        contract.price_per_unit = contract_in.price_per_unit
    if contract_in.status is not None:
        contract.status = contract_in.status

    db.commit()
    db.refresh(contract)
    return contract


@router.delete("/contracts/{contract_id}")
def delete_contract(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    farm = db.query(Farm).filter(Farm.id == contract.farm_id).first()
    if farm.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Soft delete (Change 7)
    contract.is_deleted = True
    db.commit()
    return {"message": "Contract soft-deleted successfully"}
