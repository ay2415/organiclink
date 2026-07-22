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
    return db.query(Contract).filter(Contract.farm_id == farm_id).all()


@router.put("/contracts/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: str,
    contract_in: ContractUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
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

    db.delete(contract)
    db.commit()
    return {"message": "Contract deleted successfully"}
