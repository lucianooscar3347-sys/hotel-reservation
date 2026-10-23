from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.common.validators import valider_email_domaine, valider_nom, valider_telephone

from .models import User


class IdentiteMixin:
    """Nettoyage et contrôle communs : noms et téléphone."""

    def validate_first_name(self, value):
        return valider_nom(value, 'Le prénom')

    def validate_last_name(self, value):
        return valider_nom(value, 'Le nom')

    def validate_phone(self, value):
        return valider_telephone(value) if value and value.strip() else ''


def _client_id(obj):
    profile = getattr(obj, 'client_profile', None)
    return profile.id if profile else None


class UserSerializer(IdentiteMixin, serializers.ModelSerializer):
    client_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'role', 'is_active', 'date_joined', 'client_id']
        read_only_fields = ['id', 'date_joined', 'client_id']

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_client_id(self, obj):
        return _client_id(obj)


class UserAdminSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, required=False, max_length=128)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['password']

    def validate(self, attrs):
        if not self.instance and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Le mot de passe est obligatoire.'})
        if attrs.get('password'):
            validate_password(attrs['password'])
        return attrs

    def create(self, vd):
        return User.objects.create_user(**vd)

    def update(self, instance, vd):
        password = vd.pop('password', None)
        instance = super().update(instance, vd)
        if password:
            instance.set_password(password)
            instance.save()
        return instance


class RegisterSerializer(IdentiteMixin, serializers.ModelSerializer):
    email = serializers.EmailField(max_length=254, validators=[UniqueValidator(
        queryset=User.objects.all(), lookup='iexact', message='Un compte existe déjà avec cette adresse e-mail.')])
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    phone = serializers.CharField(max_length=30)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone']
        extra_kwargs = {'first_name': {'required': True}, 'last_name': {'required': True}}

    def validate_email(self, value):
        from apps.clients.models import Client
        value = valider_email_domaine(value)
        # Une fiche client créée à l'accueil ne doit pas être rattachée sans preuve de propriété de l'e-mail.
        if Client.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Cette adresse est déjà associée à un client : contactez l\'hôtel.')
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, vd):
        from apps.clients.models import Client
        user = User.objects.create_user(role=User.Role.CLIENT, **vd)
        Client.objects.create(user=user, nom=user.last_name, prenom=user.first_name,
                              email=user.email, telephone=user.phone)
        return user


class ProfileSerializer(IdentiteMixin, serializers.ModelSerializer):
    client_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'role', 'client_id']
        read_only_fields = ['id', 'email', 'role', 'client_id']

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_client_id(self, obj):
        return _client_id(obj)

    def update(self, instance, vd):
        instance = super().update(instance, vd)
        profile = getattr(instance, 'client_profile', None)  # synchronise la fiche client
        if profile:
            profile.nom, profile.prenom, profile.telephone = instance.last_name, instance.first_name, instance.phone
            profile.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Ancien mot de passe incorrect.')
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context['request'].user)
        return value


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
