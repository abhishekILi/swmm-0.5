from typing import Any, ClassVar

from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from master.models import Department, MasterCommand

from .models import (
    CustomUser,
    CustomUserProfile,
    Designation,
    GalleryImage,
    LoginRegistrationImage,
    MasterKnowYourRegulator,
    MasterRegulatorDivision,
    Rank,
    Role,
)

# --------------------------------------------------------------------------
# Read-only master data (dropdown sources for the FE forms)
# --------------------------------------------------------------------------


class RankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rank
        fields = (
            "id",
            "name",
            "department",
        )


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = (
            "id",
            "designation_name",
        )


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = (
            "id",
            "role_name",
        )


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = (
            "id",
            "name",
            "code",
            "dep_code",
        )


class CommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterCommand
        fields = (
            "id",
            "unit_name",
            "command_name",
        )


# --------------------------------------------------------------------------
# User / profile
# --------------------------------------------------------------------------


class CustomUserProfileSerializer(serializers.ModelSerializer):
    rank_detail = RankSerializer(source="rank", read_only=True)
    designation_master_detail = DesignationSerializer(
        source="designation_master", read_only=True
    )
    department_detail = DepartmentSerializer(source="department", read_only=True)
    role_master_detail = RoleSerializer(source="role_master", read_only=True)
    command_name_detail = CommandSerializer(source="command_name", read_only=True)
    access_level_display = serializers.CharField(
        source="get_access_level_display", read_only=True
    )
    ship_name = serializers.CharField(source="ship.name", read_only=True)

    class Meta:
        model = CustomUserProfile
        fields = (
            "id",
            "rank",
            "rank_detail",
            "firstname",
            "lastname",
            "designation_master",
            "designation_master_detail",
            "designation",
            "personal_number",
            "section",
            "ship_joining_date",
            "ship_leaving_date",
            "remarks",
            "access_level",
            "access_level_display",
            "department",
            "department_detail",
            "executive_sub_department",
            "role_master",
            "role_master_detail",
            "command_name",
            "command_name_detail",
            "ship",
            "ship_name",
            "has_credentials",
            "is_role",
            "user_created_on",
            "user_active",
            "is_ood",
            "is_regulator",
            "date_of_birth",
            "date_of_joining",
            "is_married",
            "marriage_date",
            "division",
        )
        read_only_fields = (
            "id",
            "user_created_on",
        )


class CustomUserSerializer(serializers.ModelSerializer):
    profile = CustomUserProfileSerializer(source="user_profile", read_only=True)

    class Meta:
        model = CustomUser
        fields = ("id", "username", "is_active", "is_admin", "profile", "user_profile")
        read_only_fields = ("id",)
        extra_kwargs: ClassVar[dict[str, Any]] = {"user_profile": {"write_only": True}}


class CurrentUserSerializer(serializers.ModelSerializer):
    """Payload for GET /me/ — the single source the Angular app should read
    to decide what to render. See user_drf/permissions.py for how
    `capabilities` is computed."""

    profile = CustomUserProfileSerializer(source="user_profile", read_only=True)

    class Meta:
        model = CustomUser
        fields = ("id", "username", "is_active", "is_admin", "profile")


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Mirrors the account-state checks LoginView used to do (username
    normalized to uppercase, must be active with a usable profile) and embeds
    the role/access-level claims the Angular app needs for RBAC."""

    default_error_messages: ClassVar[dict[str, str]] = {
        "no_active_account": "Invalid username or password."
    }

    def validate(self, attrs):
        if attrs.get(self.username_field):
            attrs[self.username_field] = str(attrs[self.username_field]).upper()

        data = super().validate(attrs)

        profile = getattr(self.user, "user_profile", None)
        if profile is None or not profile.user_active or not profile.has_credentials:
            raise AuthenticationFailed(
                "Your account is inactive or does not have credentials.",
                "no_active_account",
            )

        data["user"] = CurrentUserSerializer(self.user).data
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["is_admin"] = bool(user.is_admin)
        profile = getattr(user, "user_profile", None)
        if profile is not None:
            token["access_level"] = profile.access_level
            token["role"] = getattr(profile.role_master, "role_name", None)
            token["department_id"] = profile.department_id
        return token


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Incorrect password."})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class RegisterProfileSerializer(serializers.Serializer):
    """Mirrors Registerview: creates a pending CustomUserProfile + CustomUser
    with the placeholder password, awaiting admin approval (is_active=False)."""

    personal_number = serializers.CharField()
    firstname = serializers.CharField()
    lastname = serializers.CharField(required=False, allow_blank=True, default="")
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    designation = serializers.PrimaryKeyRelatedField(queryset=Designation.objects.all())
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())

    def validate_personal_number(self, value):
        value = value.upper()
        if CustomUserProfile.objects.filter(personal_number=value).exists():
            raise serializers.ValidationError(
                "A profile with this personal number already exists."
            )
        return value

    def create(self, validated_data):
        department = validated_data["department"]
        rank = Rank.objects.filter(department=department).first()
        profile = CustomUserProfile.objects.create(
            rank=rank,
            firstname=validated_data["firstname"],
            lastname=validated_data.get("lastname", ""),
            designation_master=validated_data["designation"],
            department=department,
            role_master=validated_data["role"],
            personal_number=validated_data["personal_number"],
            section="NA",
            remarks="",
            has_credentials=True,
            user_active=True,
        )
        CustomUser.objects.create(
            username=profile.personal_number,
            password=make_password("12345"),
            is_active=False,
            user_profile=profile,
        )
        return profile


class DeactivateUserSerializer(serializers.Serializer):
    """Mirrors ManageUserView's form_id=2 branch / EditUserProfileView deactivation."""

    ship_leaving_date = serializers.DateTimeField(required=False, allow_null=True)

    def save(self, profile):
        user = CustomUser.objects.filter(user_profile=profile).first()
        if user is not None:
            user.is_active = False
            user.set_unusable_password()
            user.save()
        if self.validated_data.get("ship_leaving_date"):
            profile.ship_leaving_date = self.validated_data["ship_leaving_date"]
        profile.user_active = False
        profile.has_credentials = False
        profile.save()
        return profile


class MarriageDetailsSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUserProfile
        fields = ("id", "name", "personal_number", "marriage_date", "is_married")

    def get_name(self, obj):
        return f"{obj.firstname} {obj.lastname}".strip()


# --------------------------------------------------------------------------
# Regulator hierarchy ("Know Your Regulator")
# --------------------------------------------------------------------------


class MasterRegulatorDivisionSerializer(serializers.ModelSerializer):
    regulator_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = MasterRegulatorDivision
        fields = (
            "id",
            "department",
            "department_name",
            "regulator",
            "regulator_name",
            "division",
        )

    def get_regulator_name(self, obj):
        return f"{obj.regulator.firstname} {obj.regulator.lastname}".strip()


class MasterKnowYourRegulatorSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    regulator_name = serializers.SerializerMethodField()
    sailor_name = serializers.SerializerMethodField()
    division_name = serializers.CharField(
        source="division.division", read_only=True, default=None
    )

    class Meta:
        model = MasterKnowYourRegulator
        fields = (
            "id",
            "department",
            "department_name",
            "regulator",
            "regulator_name",
            "sailor",
            "sailor_name",
            "division",
            "division_name",
        )

    def get_regulator_name(self, obj):
        return f"{obj.regulator.firstname} {obj.regulator.lastname}".strip()

    def get_sailor_name(self, obj):
        if not obj.sailor:
            return None
        return f"{obj.sailor.firstname} {obj.sailor.lastname} ({obj.sailor.personal_number})"


class AssignSailorsToDivisionSerializer(serializers.Serializer):
    division = serializers.PrimaryKeyRelatedField(
        queryset=MasterRegulatorDivision.objects.all()
    )
    sailors = serializers.PrimaryKeyRelatedField(
        queryset=CustomUserProfile.objects.all(), many=True
    )

    def save(self):
        division = self.validated_data["division"]
        sailors = self.validated_data["sailors"]
        CustomUserProfile.objects.filter(division=division).update(division=None)
        CustomUserProfile.objects.filter(id__in=[s.id for s in sailors]).update(
            division=division
        )
        for sailor in sailors:
            MasterKnowYourRegulator.objects.create(
                department=division.department,
                regulator=division.regulator,
                division=division,
                sailor=sailor,
            )
        return division


# --------------------------------------------------------------------------
# Login / registration page images
# --------------------------------------------------------------------------


class LoginRegistrationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginRegistrationImage
        fields = (
            "id",
            "image",
            "name",
            "source",
            "uploaded_at",
            "uploaded_by",
            "is_active",
        )
        read_only_fields = (
            "id",
            "uploaded_at",
        )


class GalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryImage
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class PersonnelEventSerializer(serializers.Serializer):
    type = serializers.CharField()
    name = serializers.CharField()
    personal_number = serializers.CharField(
        allow_null=True,
        required=False,
    )
    designation = serializers.CharField(
        allow_blank=True,
        allow_null=True,
    )
    event_date = serializers.DateField()
    age = serializers.IntegerField(allow_null=True)
    years = serializers.IntegerField(allow_null=True)
    event_label = serializers.CharField()


class PersonnelEventResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    today = PersonnelEventSerializer(many=True)
    tomorrow = PersonnelEventSerializer(many=True)
    upcoming = PersonnelEventSerializer(many=True)
    results = PersonnelEventSerializer(many=True)
