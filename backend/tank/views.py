"""
DRF Views and ViewSets for the Tank Module.
Enforces PEP 8 compliance and RESTful API standards.
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Fluid,
    FluidInTank,
    FluidType,
    FuellingDetails,
    Hierarchyforchart,
    MeasurementFuelsondingFinal,
    SoundingDraft,
    TankCategory,
    TankFluidUnit,
    TankFuelSounding,
    TankLocation,
    TankOil,
    TankRecord,
    TankSoundingData,
    TankSoundingMaster,
    TankTypeDetail,
)
from .serializers import (
    FluidInTankSerializer,
    FluidSerializer,
    FluidTypeSerializer,
    FuellingDetailsSerializer,
    FuelSoundingSerializer,
    HierarchyforchartSerializer,
    SoundingDraftSerializer,
    TankCategorySerializer,
    TankFluidUnitSerializer,
    TankFuelSoundingSerializer,
    TankLocationSerializer,
    TankOilSerializer,
    TankRecordSerializer,
    TankSoundingDataSerializer,
    TankSoundingMasterSerializer,
    TankTypeDetailSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Base ModelViewSet for Tank Read/Write Operations
# ─────────────────────────────────────────────────────────────


class BaseReadWriteViewSet(viewsets.ModelViewSet):
    """Base ViewSet enforcing standard REST response format."""

    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "status": "success",
                **serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                "status": "success",
                **serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        model_name = self.queryset.model._meta.verbose_name.title()
        return Response(
            {
                "status": "success",
                "message": f"{model_name} deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────────────────────
# Granular Model ViewSets
# ─────────────────────────────────────────────────────────────


@extend_schema(tags=["Tank"])
class TankFluidUnitViewSet(BaseReadWriteViewSet):
    queryset = TankFluidUnit.objects.all().order_by("id")
    serializer_class = TankFluidUnitSerializer


@extend_schema(tags=["Tank"])
class TankTypeDetailViewSet(BaseReadWriteViewSet):
    queryset = TankTypeDetail.objects.all().order_by("id")
    serializer_class = TankTypeDetailSerializer


@extend_schema(tags=["Tank"])
class TankSoundingMasterViewSet(BaseReadWriteViewSet):
    queryset = TankSoundingMaster.objects.all().order_by("id")
    serializer_class = TankSoundingMasterSerializer


@extend_schema(tags=["Tank"])
class TankSoundingDataViewSet(BaseReadWriteViewSet):
    queryset = TankSoundingData.objects.all().order_by("id")
    serializer_class = TankSoundingDataSerializer


@extend_schema(tags=["Tank"])
class MeasurementViewSet(BaseReadWriteViewSet):
    queryset = MeasurementFuelsondingFinal.objects.all().order_by("id")
    serializer_class = FuelSoundingSerializer


@extend_schema(tags=["Tank"])
class TankCategoryViewSet(BaseReadWriteViewSet):
    queryset = TankCategory.objects.all().order_by("id")
    serializer_class = TankCategorySerializer


@extend_schema(tags=["Tank"])
class FluidTypeViewSet(BaseReadWriteViewSet):
    queryset = FluidType.objects.all().order_by("id")
    serializer_class = FluidTypeSerializer


@extend_schema(tags=["Tank"])
class FluidViewSet(BaseReadWriteViewSet):
    queryset = Fluid.objects.all().order_by("id")
    serializer_class = FluidSerializer


@extend_schema(tags=["Tank"])
class TankLocationViewSet(BaseReadWriteViewSet):
    queryset = TankLocation.objects.all().order_by("id")
    serializer_class = TankLocationSerializer


@extend_schema(tags=["Tank"])
class TankOilViewSet(BaseReadWriteViewSet):
    queryset = TankOil.objects.all().order_by("id")
    serializer_class = TankOilSerializer


@extend_schema(tags=["Tank"])
class FuellingDetailsViewSet(BaseReadWriteViewSet):
    queryset = FuellingDetails.objects.all().order_by("id")
    serializer_class = FuellingDetailsSerializer


@extend_schema(tags=["Tank"])
class FluidInTankViewSet(BaseReadWriteViewSet):
    queryset = FluidInTank.objects.all().order_by("id")
    serializer_class = FluidInTankSerializer


@extend_schema(tags=["Tank"])
class TankRecordViewSet(BaseReadWriteViewSet):
    queryset = TankRecord.objects.all().order_by("id")
    serializer_class = TankRecordSerializer


@extend_schema(tags=["Tank"])
class SoundingDraftViewSet(BaseReadWriteViewSet):
    queryset = SoundingDraft.objects.all().order_by("id")
    serializer_class = SoundingDraftSerializer


@extend_schema(tags=["Tank"])
class TankFuelSoundingViewSet(BaseReadWriteViewSet):
    queryset = TankFuelSounding.objects.all().order_by("id")
    serializer_class = TankFuelSoundingSerializer


@extend_schema(tags=["Tank"])
class HierarchyforchartViewSet(BaseReadWriteViewSet):
    queryset = Hierarchyforchart.objects.all().order_by("id")
    serializer_class = HierarchyforchartSerializer


# ─────────────────────────────────────────────────────────────
# Workflow & Specialized APIViews
# ─────────────────────────────────────────────────────────────


class TankDashboardAPIView(APIView):
    """
    Returns high-level summary and dashboard metrics for all ship tanks.
    """

    def get(self, request):
        tanks = TankRecord.objects.all()
        serializer = TankRecordSerializer(tanks, many=True)
        return Response(
            {
                "status": "success",
                "total_tanks": tanks.count(),
                "tanks": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class TankDetailAPIView(APIView):
    """
    Retrieves full details of a specific tank by ID.
    """

    def get(self, request, tank_id):
        tank = get_object_or_404(TankRecord, pk=tank_id)
        serializer = TankRecordSerializer(tank)
        return Response(
            {
                "status": "success",
                "tank": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class FuellingHistoryAPIView(APIView):
    """
    Returns fuelling history logs and active fuelling operations.
    """

    def get(self, request):
        records = FuellingDetails.objects.all().order_by("-id")
        serializer = FuellingDetailsSerializer(records, many=True)
        return Response(
            {
                "status": "success",
                "fuelling_history": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class FuellingSaveAPIView(APIView):
    """
    Creates or updates a fuelling detail entry.
    """

    @transaction.atomic
    def post(self, request):
        serializer = FuellingDetailsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "status": "success",
                "message": "Fuelling details saved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class TankRASMonitorAPIView(APIView):
    """
    Returns RAS (Replenishment at Sea) monitoring data for a specific tank or vessel.
    """

    def get(self, request, id):
        fuelling = FuellingDetails.objects.filter(pk=id).first()
        data = FuellingDetailsSerializer(fuelling).data if fuelling else {}
        return Response(
            {
                "status": "success",
                "ras_monitor": data,
            },
            status=status.HTTP_200_OK,
        )


class TankCalibrationAPIView(APIView):
    """
    Retrieves sounding calibration data for a specified tank.
    """

    def get(self, request):
        tank_id = request.query_params.get("tank_id")
        soundings = TankSoundingData.objects.all()
        if tank_id:
            soundings = soundings.filter(tank_category_detail_id=tank_id)
        serializer = TankSoundingDataSerializer(soundings, many=True)
        return Response(
            {
                "status": "success",
                "calibrations": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
