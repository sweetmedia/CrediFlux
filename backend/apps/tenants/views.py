"""
API views for Tenant management
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import (
    TenantRegistrationSerializer,
    TenantSerializer,
    TenantLoginSerializer,
    TenantUpdateSerializer
)


class TenantRegistrationView(APIView):
    """
    Public endpoint for registering a new tenant (company).

    This endpoint allows companies to register for the SaaS platform.
    It creates:
    - A new Tenant
    - A primary Domain for the tenant
    - An owner User account with admin privileges

    **Authentication:** Not required (public endpoint)

    **Permissions:** Anyone can register a new tenant
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='register_tenant',
        operation_description='Register a new tenant with owner user',
        request_body=TenantRegistrationSerializer,
        responses={
            201: openapi.Response(
                description='Tenant registered successfully',
                examples={
                    'application/json': {
                        'tenant': {
                            'id': 1,
                            'name': 'acme-corp',
                            'business_name': 'ACME Corporation',
                            'email': 'contact@acme.com',
                            'subscription_plan': 'basic',
                            'is_active': True
                        },
                        'domain': {
                            'domain': 'acme.localhost',
                            'is_primary': True
                        },
                        'owner': {
                            'id': 1,
                            'email': 'john@acme.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'is_tenant_owner': True
                        },
                        'message': 'Tenant registered successfully! Please check your email to verify your account.',
                        'next_steps': [
                            'Verify your email address',
                            'Login to your tenant admin panel',
                            'Start creating loans and managing customers'
                        ]
                    }
                }
            ),
            400: openapi.Response(
                description='Bad request - validation errors',
                examples={
                    'application/json': {
                        'tenant_name': ['A tenant with this name already exists.'],
                        'owner_email': ['A user with this email already exists.']
                    }
                }
            ),
            500: openapi.Response(
                description='Server error',
                examples={
                    'application/json': {
                        'error': 'Failed to create tenant: Internal server error'
                    }
                }
            )
        },
        tags=['Tenant Registration']
    )
    def post(self, request):
        """
        Register a new tenant (company) with owner user.

        Example request body:
        ```json
        {
            "business_name": "ACME Corporation",
            "tenant_name": "acme-corp",
            "tax_id": "12-3456789",
            "email": "contact@acme.com",
            "phone": "+1234567890",
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "country": "USA",
            "postal_code": "10001",
            "subdomain": "acme",
            "owner_first_name": "John",
            "owner_last_name": "Doe",
            "owner_email": "john@acme.com",
            "owner_password": "SecurePass123!",
            "owner_phone": "+1234567890",
            "subscription_plan": "basic"
        }
        ```
        """
        serializer = TenantRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # Create tenant, domain, and owner user
                result = serializer.save()

                # Return success response
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response(
                    {'error': f'Failed to create tenant: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Return validation errors
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class TenantHealthCheckView(APIView):
    """
    Simple health check endpoint to verify the tenant registration API is working.

    **Authentication:** Not required (public endpoint)
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='tenant_health_check',
        operation_description='Check if tenant registration API is available',
        responses={
            200: openapi.Response(
                description='API is healthy',
                examples={
                    'application/json': {
                        'status': 'healthy',
                        'service': 'tenant-registration',
                        'message': 'Tenant registration API is operational'
                    }
                }
            )
        },
        tags=['Tenant Registration']
    )
    def get(self, request):
        """
        Health check for tenant registration API.
        """
        return Response({
            'status': 'healthy',
            'service': 'tenant-registration',
            'message': 'Tenant registration API is operational',
            'endpoints': {
                'register': '/api/tenants/register/',
                'login': '/api/tenants/login/',
                'health': '/api/tenants/health/',
            }
        })


class TenantLoginView(APIView):
    """
    Public endpoint for tenant user login.

    This endpoint authenticates users and returns JWT tokens along with
    user and tenant information.

    **Authentication:** Not required (public endpoint)

    **Validations:**
    - User credentials are correct
    - User account is active
    - Tenant account is active (if applicable)
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='tenant_login',
        operation_description='Login with email and password to get JWT tokens',
        request_body=TenantLoginSerializer,
        responses={
            200: openapi.Response(
                description='Login successful',
                examples={
                    'application/json': {
                        'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                        'user': {
                            'id': 3,
                            'email': 'john@testcompany.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'full_name': 'John Doe',
                            'role': 'admin',
                            'is_tenant_owner': True,
                            'is_staff': True,
                            'is_superuser': False
                        },
                        'tenant': {
                            'id': 6,
                            'name': 'testcompany',
                            'business_name': 'Test Company LLC',
                            'subscription_plan': 'basic',
                            'is_active': True,
                            'domain': 'testcompany'
                        },
                        'message': 'Login successful'
                    }
                }
            ),
            400: openapi.Response(
                description='Bad request - validation errors',
                examples={
                    'application/json': {
                        'non_field_errors': ['Invalid email or password.']
                    }
                }
            ),
            403: openapi.Response(
                description='Account deactivated',
                examples={
                    'application/json': {
                        'non_field_errors': ['This account has been deactivated. Please contact support.']
                    }
                }
            )
        },
        tags=['Authentication']
    )
    def post(self, request):
        """
        Authenticate user and return JWT tokens.

        Example request body:
        ```json
        {
            "email": "john@testcompany.com",
            "password": "SecurePass123!"
        }
        ```

        Returns:
        - access_token: JWT access token (expires in 60 minutes by default)
        - refresh_token: JWT refresh token (expires in 24 hours by default)
        - user: User information including role and permissions
        - tenant: Tenant information (if user belongs to a tenant)
        """
        serializer = TenantLoginSerializer(data=request.data)

        if serializer.is_valid():
            # Get validated data
            validated_data = serializer.validated_data

            # Create instance to trigger to_representation
            response_serializer = TenantLoginSerializer(validated_data)

            # Return tokens and user/tenant info
            return Response(
                response_serializer.to_representation(validated_data),
                status=status.HTTP_200_OK
            )

        # Return validation errors
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class TenantSettingsView(APIView):
    """
    Endpoint for retrieving and updating current tenant settings.

    **GET:** Get current tenant information
    **PUT/PATCH:** Update current tenant settings

    **Authentication:** Required (user must be logged in)
    **Permissions:** User must belong to a tenant
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='get_tenant_settings',
        operation_description='Get current tenant information and settings',
        responses={
            200: openapi.Response(
                description='Tenant information retrieved successfully',
                schema=TenantSerializer
            ),
            403: openapi.Response(
                description='User does not belong to a tenant',
                examples={
                    'application/json': {
                        'error': 'You do not belong to any tenant.'
                    }
                }
            )
        },
        tags=['Tenant Settings']
    )
    def get(self, request):
        """
        Get current tenant information.

        Returns all tenant details including business information, address, and settings.
        """
        # Get user's tenant
        user = request.user

        if not user.tenant:
            return Response(
                {'error': 'You do not belong to any tenant.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TenantSerializer(user.tenant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id='update_tenant_settings',
        operation_description='Update current tenant settings',
        request_body=TenantUpdateSerializer,
        responses={
            200: openapi.Response(
                description='Tenant settings updated successfully',
                schema=TenantSerializer
            ),
            400: openapi.Response(
                description='Validation error',
                examples={
                    'application/json': {
                        'email': ['This field is required.'],
                        'business_name': ['Business name must be at least 2 characters long.']
                    }
                }
            ),
            403: openapi.Response(
                description='Permission denied',
                examples={
                    'application/json': {
                        'error': 'You do not have permission to update tenant settings.'
                    }
                }
            )
        },
        tags=['Tenant Settings']
    )
    def put(self, request):
        """
        Update current tenant settings (full update).

        Example request body:
        ```json
        {
            "business_name": "Updated Company Name",
            "tax_id": "12-3456789",
            "email": "contact@company.com",
            "phone": "+1234567890",
            "address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "country": "USA",
            "postal_code": "10001",
            "primary_color": "#6366f1"
        }
        ```
        """
        return self._update_tenant(request, partial=False)

    @swagger_auto_schema(
        operation_id='partial_update_tenant_settings',
        operation_description='Partially update current tenant settings',
        request_body=TenantUpdateSerializer,
        responses={
            200: openapi.Response(
                description='Tenant settings updated successfully',
                schema=TenantSerializer
            ),
            400: 'Validation error',
            403: 'Permission denied'
        },
        tags=['Tenant Settings']
    )
    def patch(self, request):
        """
        Partially update current tenant settings.

        You can update only the fields you want to change.
        """
        return self._update_tenant(request, partial=True)

    def _update_tenant(self, request, partial=False):
        """Helper method to update tenant"""
        user = request.user

        # Check if user belongs to a tenant
        if not user.tenant:
            return Response(
                {'error': 'You do not belong to any tenant.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user has permission (owner or admin)
        if not (user.is_tenant_owner or user.role == 'admin'):
            return Response(
                {'error': 'You do not have permission to update tenant settings.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Update tenant
        serializer = TenantUpdateSerializer(
            user.tenant,
            data=request.data,
            partial=partial
        )

        if serializer.is_valid():
            serializer.save()

            # Return updated tenant data
            response_serializer = TenantSerializer(user.tenant)
            return Response(
                {
                    'message': 'Tenant settings updated successfully.',
                    'tenant': response_serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
