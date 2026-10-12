"""
Service layer for Phase 21 — Non-Motor Commercial Insurance Lines of Business & Operations.
Implements:
1. Product classes & product catalogs (BLL_Class, BLL_NonMotorProductType)
2. Business types & document types (BLL_NonMotorBusiness, BLL_NonMotorDocument)
3. Endorsement types & sub-types (BLL_NonMotorEndorsmentType, BLL_NonMotorEndorsmentSubType)
4. Insurer types & sub-types (BLL_NonMotor)
5. Non-motor commission grid management & calculation engine (BLL_NonMotor)
6. Non-motor policy & proposal transaction processing (BLL_NonMotorTransaction)
"""
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.phase21_nonmotor import (
    NonMotorClass,
    NonMotorProduct,
    NonMotorBusinessType,
    NonMotorDocumentType,
    NonMotorEndorsementType,
    NonMotorEndorsementSubType,
    NonMotorInsuranceType,
    NonMotorInsuranceSubType,
    NonMotorTypeOfInsuranceSubType,
    NonMotorCommission,
    NonMotorTransaction,
)
from app.schemas.phase21_nonmotor import (
    NonMotorClassCreate,
    NonMotorClassUpdate,
    NonMotorProductCreate,
    NonMotorProductUpdate,
    NonMotorBusinessTypeCreate,
    NonMotorBusinessTypeUpdate,
    NonMotorDocumentTypeCreate,
    NonMotorDocumentTypeUpdate,
    NonMotorEndorsementTypeCreate,
    NonMotorEndorsementTypeUpdate,
    NonMotorEndorsementSubTypeCreate,
    NonMotorEndorsementSubTypeUpdate,
    NonMotorInsuranceTypeCreate,
    NonMotorInsuranceSubTypeCreate,
    NonMotorTypeOfInsuranceSubTypeCreate,
    NonMotorCommissionCreate,
    NonMotorCommissionUpdate,
    NonMotorCommissionCalculationRequest,
    NonMotorCommissionCalculationResponse,
    NonMotorTransactionCreate,
    NonMotorTransactionUpdate,
    NonMotorDashboardSummaryResponse,
)


class NonMotorService:
    """
    Business logic and transactional persistence for Non-Motor Insurance Operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # =========================================================================
    # 1. Product Classes & Products
    # =========================================================================

    async def list_classes(self, is_active: Optional[int] = None) -> List[NonMotorClass]:
        stmt = select(NonMotorClass)
        if is_active is not None:
            stmt = stmt.where(NonMotorClass.IsActive == is_active)
        stmt = stmt.order_by(NonMotorClass.Class)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_class(self, class_id: int) -> NonMotorClass:
        stmt = select(NonMotorClass).where(NonMotorClass.ClassId == class_id)
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Non-motor product class {class_id} not found",
            )
        return instance

    async def create_class(self, payload: NonMotorClassCreate, username: str) -> NonMotorClass:
        instance = NonMotorClass(
            Class=payload.Class.strip(),
            IsActive=payload.IsActive if payload.IsActive is not None else 1,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def update_class(
        self, class_id: int, payload: NonMotorClassUpdate, username: str
    ) -> NonMotorClass:
        instance = await self.get_class(class_id)
        if payload.Class is not None:
            instance.Class = payload.Class.strip()
        if payload.IsActive is not None:
            instance.IsActive = payload.IsActive
        instance.UpdatedBy = username
        instance.UpdatedDate = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def list_products(
        self, class_id: Optional[int] = None, is_active: Optional[int] = None
    ) -> List[NonMotorProduct]:
        stmt = select(NonMotorProduct)
        conditions = []
        if class_id is not None:
            conditions.append(NonMotorProduct.ClassId == class_id)
        if is_active is not None:
            conditions.append(NonMotorProduct.IsActive == is_active)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(NonMotorProduct.ProductType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_product(self, product_id: int) -> NonMotorProduct:
        stmt = select(NonMotorProduct).where(NonMotorProduct.NonMotorProductId == product_id)
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Non-motor product {product_id} not found",
            )
        return instance

    async def create_product(self, payload: NonMotorProductCreate, username: str) -> NonMotorProduct:
        # Validate parent class exists
        await self.get_class(payload.ClassId)
        instance = NonMotorProduct(
            ClassId=payload.ClassId,
            ProductType=payload.ProductType.strip(),
            ProductCode=payload.ProductCode.strip() if payload.ProductCode else None,
            IsActive=payload.IsActive if payload.IsActive is not None else 1,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def update_product(
        self, product_id: int, payload: NonMotorProductUpdate, username: str
    ) -> NonMotorProduct:
        instance = await self.get_product(product_id)
        if payload.ClassId is not None:
            await self.get_class(payload.ClassId)
            instance.ClassId = payload.ClassId
        if payload.ProductType is not None:
            instance.ProductType = payload.ProductType.strip()
        if payload.ProductCode is not None:
            instance.ProductCode = payload.ProductCode.strip()
        if payload.IsActive is not None:
            instance.IsActive = payload.IsActive
        instance.UpdatedBy = username
        instance.UpdatedDate = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    # =========================================================================
    # 2. Business Types & Required Document Types
    # =========================================================================

    async def list_business_types(self, is_active: Optional[int] = None) -> List[NonMotorBusinessType]:
        stmt = select(NonMotorBusinessType)
        if is_active is not None:
            stmt = stmt.where(NonMotorBusinessType.IsActive == is_active)
        stmt = stmt.order_by(NonMotorBusinessType.BusinessType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_business_type(
        self, payload: NonMotorBusinessTypeCreate, username: str
    ) -> NonMotorBusinessType:
        instance = NonMotorBusinessType(
            BusinessType=payload.BusinessType.strip(),
            IsActive=payload.IsActive if payload.IsActive is not None else 1,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def list_document_types(self, is_active: Optional[int] = None) -> List[NonMotorDocumentType]:
        stmt = select(NonMotorDocumentType)
        if is_active is not None:
            stmt = stmt.where(NonMotorDocumentType.IsActive == is_active)
        stmt = stmt.order_by(NonMotorDocumentType.DocumentType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_document_type(
        self, payload: NonMotorDocumentTypeCreate, username: str
    ) -> NonMotorDocumentType:
        instance = NonMotorDocumentType(
            DocumentType=payload.DocumentType.strip(),
            IsActive=payload.IsActive if payload.IsActive is not None else 1,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    # =========================================================================
    # 3. Endorsement Hierarchy
    # =========================================================================

    async def list_endorsement_types(self, is_active: Optional[int] = None) -> List[NonMotorEndorsementType]:
        stmt = select(NonMotorEndorsementType)
        if is_active is not None:
            stmt = stmt.where(NonMotorEndorsementType.IsActive == is_active)
        stmt = stmt.order_by(NonMotorEndorsementType.EndorsementType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_endorsement_type(
        self, payload: NonMotorEndorsementTypeCreate, username: str
    ) -> NonMotorEndorsementType:
        instance = NonMotorEndorsementType(
            EndorsementType=payload.EndorsementType.strip(),
            IsActive=payload.IsActive if payload.IsActive is not None else 1,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def list_endorsement_sub_types(
        self, endorsement_id: Optional[int] = None, is_active: Optional[int] = None
    ) -> List[NonMotorEndorsementSubType]:
        stmt = select(NonMotorEndorsementSubType)
        conditions = []
        if endorsement_id is not None:
            conditions.append(NonMotorEndorsementSubType.NonEndorsementId == endorsement_id)
        if is_active is not None:
            conditions.append(NonMotorEndorsementSubType.IsActive == is_active)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(NonMotorEndorsementSubType.EndorsementSubType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_endorsement_sub_type(
        self, payload: NonMotorEndorsementSubTypeCreate, username: str
    ) -> NonMotorEndorsementSubType:
        # Validate parent endorsement type
        stmt = select(NonMotorEndorsementType).where(
            NonMotorEndorsementType.NonEndorsementId == payload.NonEndorsementId
        )
        res = await self.session.execute(stmt)
        if not res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Endorsement Type {payload.NonEndorsementId} not found",
            )
        instance = NonMotorEndorsementSubType(
            NonEndorsementId=payload.NonEndorsementId,
            EndorsementSubType=payload.EndorsementSubType.strip(),
            IsActive=payload.IsActive if payload.IsActive is not None else 1,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    # =========================================================================
    # 4. Insurer Insurance Types & Sub-Types
    # =========================================================================

    async def list_insurance_types(self, company_id: Optional[int] = None) -> List[NonMotorInsuranceType]:
        stmt = select(NonMotorInsuranceType).where(NonMotorInsuranceType.IsDeleted == 0)
        if company_id is not None:
            stmt = stmt.where(NonMotorInsuranceType.InsuranceCompanyId == company_id)
        stmt = stmt.order_by(NonMotorInsuranceType.InsuranceType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_insurance_type(
        self, payload: NonMotorInsuranceTypeCreate, username: str
    ) -> NonMotorInsuranceType:
        instance = NonMotorInsuranceType(
            InsuranceType=payload.InsuranceType.strip(),
            InsuranceCompanyId=payload.InsuranceCompanyId,
            Flag=payload.Flag,
            IsDeleted=0,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def list_insurance_sub_types(
        self, type_id: Optional[int] = None
    ) -> List[NonMotorInsuranceSubType]:
        stmt = select(NonMotorInsuranceSubType).where(NonMotorInsuranceSubType.IsDeleted == 0)
        if type_id is not None:
            stmt = stmt.where(NonMotorInsuranceSubType.InsuranceTypeId == type_id)
        stmt = stmt.order_by(NonMotorInsuranceSubType.InsuranceSubType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_insurance_sub_type(
        self, payload: NonMotorInsuranceSubTypeCreate, username: str
    ) -> NonMotorInsuranceSubType:
        instance = NonMotorInsuranceSubType(
            InsuranceSubType=payload.InsuranceSubType.strip(),
            InsuranceTypeId=payload.InsuranceTypeId,
            Flag=payload.Flag,
            IsDeleted=0,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def list_types_of_sub_type(
        self, sub_type_id: Optional[int] = None
    ) -> List[NonMotorTypeOfInsuranceSubType]:
        stmt = select(NonMotorTypeOfInsuranceSubType).where(NonMotorTypeOfInsuranceSubType.IsDeleted == 0)
        if sub_type_id is not None:
            stmt = stmt.where(NonMotorTypeOfInsuranceSubType.InsuranceSubTypeId == sub_type_id)
        stmt = stmt.order_by(NonMotorTypeOfInsuranceSubType.TypeOfSubType)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_type_of_sub_type(
        self, payload: NonMotorTypeOfInsuranceSubTypeCreate, username: str
    ) -> NonMotorTypeOfInsuranceSubType:
        instance = NonMotorTypeOfInsuranceSubType(
            TypeOfSubType=payload.TypeOfSubType.strip(),
            InsuranceTypeId=payload.InsuranceTypeId,
            InsuranceSubTypeId=payload.InsuranceSubTypeId,
            Flag=payload.Flag,
            IsDeleted=0,
            CreatedBy=username,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    # =========================================================================
    # 5. Non-Motor Commission Grids & Calculations
    # =========================================================================

    async def list_commissions(
        self,
        company_id: Optional[int] = None,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        is_active: Optional[int] = 1,
    ) -> List[NonMotorCommission]:
        stmt = select(NonMotorCommission)
        conditions = []
        if company_id is not None:
            conditions.append(NonMotorCommission.InsuranceCompanyId == company_id)
        if reference_id is not None:
            conditions.append(NonMotorCommission.ReferanceId == reference_id)
        if reference_type is not None:
            conditions.append(func.lower(NonMotorCommission.ReferenceType) == reference_type.strip().lower())
        if is_active is not None:
            conditions.append(NonMotorCommission.IsActive == is_active)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(NonMotorCommission.NonMotorCommId.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_commission(
        self, payload: NonMotorCommissionCreate, user_id: int
    ) -> NonMotorCommission:
        instance = NonMotorCommission(
            InsuranceCompanyId=payload.InsuranceCompanyId,
            InsuranceTypeId=payload.InsuranceTypeId,
            InsuranceSubTypeId=payload.InsuranceSubTypeId or 0,
            TypeSubTypeId=payload.TypeSubTypeId or 0,
            ReferanceId=payload.ReferanceId,
            ReferenceType=payload.ReferenceType.strip(),
            Commission=payload.Commission,
            CommissionCalculateOn=payload.CommissionCalculateOn or "NetPremium",
            ValidFromDate=payload.ValidFromDate or date.today(),
            Extra1=payload.Extra1,
            Extra2=payload.Extra2,
            IsActive=payload.IsActive if payload.IsActive is not None else 1,
            CreateUser=user_id,
            CreateDate=datetime.utcnow(),
        )
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def calculate_commission(
        self, req: NonMotorCommissionCalculationRequest
    ) -> NonMotorCommissionCalculationResponse:
        # Search matching grid record
        stmt = select(NonMotorCommission).where(
            and_(
                NonMotorCommission.InsuranceCompanyId == req.InsuranceCompanyId,
                NonMotorCommission.InsuranceTypeId == req.InsuranceTypeId,
                NonMotorCommission.ReferanceId == req.ReferanceId,
                func.lower(NonMotorCommission.ReferenceType) == req.ReferenceType.strip().lower(),
                NonMotorCommission.IsActive == 1,
            )
        )
        if req.InsuranceSubTypeId:
            stmt = stmt.where(NonMotorCommission.InsuranceSubTypeId == req.InsuranceSubTypeId)
        stmt = stmt.order_by(NonMotorCommission.ValidFromDate.desc(), NonMotorCommission.NonMotorCommId.desc())
        res = await self.session.execute(stmt)
        grid_record = res.scalars().first()

        rate = grid_record.Commission if grid_record else Decimal("0.00")
        gross_commission = (req.NetPremium * rate / Decimal("100.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        tds_rate = req.TdsRate or Decimal("5.00")
        tds_amount = (gross_commission * tds_rate / Decimal("100.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        net_commission = (gross_commission - tds_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return NonMotorCommissionCalculationResponse(
            CommissionRate=rate,
            NetPremium=req.NetPremium,
            GrossCommission=gross_commission,
            TdsRate=tds_rate,
            TdsAmount=tds_amount,
            NetCommission=net_commission,
            ReferenceType=req.ReferenceType,
            ReferanceId=req.ReferanceId,
        )

    # =========================================================================
    # 6. Non-Motor Policy & Proposal Transactions
    # =========================================================================

    async def _generate_nonmotor_inward_no(self, branch_id: int) -> str:
        today_str = datetime.utcnow().strftime("%Y%m%d")
        # Find count for today
        stmt = select(func.count(NonMotorTransaction.NonMotorTransactionId)).where(
            NonMotorTransaction.InwardNo.like(f"INW-NM-{today_str}-%")
        )
        res = await self.session.execute(stmt)
        seq = (res.scalar() or 0) + 1
        return f"INW-NM-{today_str}-{seq:04d}"

    async def create_transaction(
        self, payload: NonMotorTransactionCreate, username: str
    ) -> NonMotorTransaction:
        # Validate product and class
        await self.get_class(payload.ClassId)
        await self.get_product(payload.ProductTypeId)

        inward_no = await self._generate_nonmotor_inward_no(payload.BranchId)

        # Calculate agent commission
        rate = payload.AgentComm or Decimal("0.00")
        gross_comm = (payload.NetPermium * rate / Decimal("100.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        tds_rate = payload.TdsRate or Decimal("5.00")
        tds_amt = (gross_comm * tds_rate / Decimal("100.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        net_comm = (gross_comm - tds_amt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_amount = (payload.NetPermium + gross_comm).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        now_dt = datetime.utcnow()
        tx = NonMotorTransaction(
            InwardNo=inward_no,
            TransDate=now_dt,
            BranchId=payload.BranchId,
            CustomerId=payload.CustomerId,
            InsuranceCompanyId=payload.InsuranceCompanyId,
            CoverNote=payload.CoverNote,
            PreviousPolicyNo=payload.PreviousPolicyNo,
            PolicyNo=payload.PolicyNo,
            CnIssueDate=payload.CnIssueDate or now_dt,
            ClassId=payload.ClassId,
            ProductTypeId=payload.ProductTypeId,
            BusinessTypeId=payload.BusinessTypeId,
            NonDocumentTypeId=payload.NonDocumentTypeId,
            NonEndorsementId=payload.NonEndorsementId,
            NonEndorsesubId=payload.NonEndorsesubId,
            EndorsementReason=payload.EndorsementReason,
            AgentId=payload.AgentId,
            SalesEx_id=payload.SalesEx_id,
            RiskStartdate=payload.RiskStartdate or now_dt,
            ExpiryDate=payload.ExpiryDate,
            SumInsured=payload.SumInsured,
            NetPermium=payload.NetPermium,
            ProPosalAmt=payload.ProPosalAmt or Decimal("0.00"),
            Remark=payload.Remark,
            ReferenceType=payload.ReferenceType or "Agent",
            ReferenceBy=payload.ReferenceBy,
            ReferenceRole=payload.ReferenceRole,
            PersonName=payload.PersonName,
            tat=payload.tat,
            AgentComm=rate,
            AgentCommAmt=gross_comm,
            TdsAmt=tds_amt,
            NetCommission=net_comm,
            Amount=total_amount,
            TStatus="Active",
            CreateDate=now_dt,
            CreateUser=username,
        )
        self.session.add(tx)
        await self.session.commit()
        await self.session.refresh(tx)
        return tx

    async def get_transaction(self, trans_id: int) -> NonMotorTransaction:
        stmt = select(NonMotorTransaction).where(
            NonMotorTransaction.NonMotorTransactionId == trans_id
        )
        res = await self.session.execute(stmt)
        tx = res.scalar_one_or_none()
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Non-motor transaction {trans_id} not found",
            )
        return tx

    async def list_transactions(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        branch_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[NonMotorTransaction]:
        stmt = select(NonMotorTransaction)
        conditions = []
        if from_date is not None:
            conditions.append(NonMotorTransaction.TransDate >= from_date)
        if to_date is not None:
            conditions.append(NonMotorTransaction.TransDate <= to_date)
        if branch_id is not None:
            conditions.append(NonMotorTransaction.BranchId == branch_id)
        if customer_id is not None:
            conditions.append(NonMotorTransaction.CustomerId == customer_id)
        if agent_id is not None:
            conditions.append(NonMotorTransaction.AgentId == agent_id)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(NonMotorTransaction.NonMotorTransactionId.desc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_transaction(
        self, trans_id: int, payload: NonMotorTransactionUpdate, username: str
    ) -> NonMotorTransaction:
        tx = await self.get_transaction(trans_id)
        if payload.PolicyNo is not None:
            tx.PolicyNo = payload.PolicyNo.strip()
        if payload.CnIssueDate is not None:
            tx.CnIssueDate = payload.CnIssueDate
        if payload.CoverNote is not None:
            tx.CoverNote = payload.CoverNote.strip()
        if payload.Remark is not None:
            tx.Remark = payload.Remark.strip()
        if payload.TStatus is not None:
            tx.TStatus = payload.TStatus.strip()
        tx.UpdateUser = username
        tx.UpdateDate = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(tx)
        return tx

    async def get_dashboard_summary(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        branch_id: Optional[int] = None,
    ) -> NonMotorDashboardSummaryResponse:
        conditions = []
        if from_date is not None:
            conditions.append(NonMotorTransaction.TransDate >= from_date)
        if to_date is not None:
            conditions.append(NonMotorTransaction.TransDate <= to_date)
        if branch_id is not None:
            conditions.append(NonMotorTransaction.BranchId == branch_id)

        base_stmt = select(
            func.count(NonMotorTransaction.NonMotorTransactionId),
            func.coalesce(func.sum(NonMotorTransaction.NetPermium), 0),
            func.coalesce(func.sum(NonMotorTransaction.AgentCommAmt), 0),
        )
        if conditions:
            base_stmt = base_stmt.where(and_(*conditions))
        res = await self.session.execute(base_stmt)
        tot_cnt, tot_prem, tot_comm = res.one()

        # Breakdown by product class
        class_stmt = (
            select(
                NonMotorClass.Class,
                func.count(NonMotorTransaction.NonMotorTransactionId),
                func.coalesce(func.sum(NonMotorTransaction.NetPermium), 0),
            )
            .join(NonMotorClass, NonMotorTransaction.ClassId == NonMotorClass.ClassId)
        )
        if conditions:
            class_stmt = class_stmt.where(and_(*conditions))
        class_stmt = class_stmt.group_by(NonMotorClass.Class)
        c_res = await self.session.execute(class_stmt)
        by_class = [
            {"class_name": r[0], "count": r[1], "net_premium": Decimal(str(r[2]))}
            for r in c_res.all()
        ]

        return NonMotorDashboardSummaryResponse(
            total_policies=tot_cnt,
            total_net_premium=Decimal(str(tot_prem)),
            total_commission_paid=Decimal(str(tot_comm)),
            by_product_class=by_class,
        )
