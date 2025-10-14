from django.urls import path
from django.urls import re_path


from dfd.health import HealthView, TestView, TestProjectsView
from .views import (
    # Users
    DiagramBulkSyncView, UserListCreateView, UserDetailView,
    # Projects
    ProjectListCreateView, ProjectDetailView,
    # Diagrams
    DiagramListCreateView, DiagramDetailView,
    # Components
    ComponentListCreateUnderDiagramView, ComponentDetailUnderDiagramView,
    # Threats
    ThreatListCreateView, ThreatDetailView,
    # Trust Boundaries
    TrustBoundaryListCreateView, TrustBoundaryDetailView,
    # Threat Assessment
    ThreatAssessmentView,
)

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('test/', TestView.as_view(), name='test'),
    path('test-projects/', TestProjectsView.as_view(), name='test-projects'),

    # Users
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<str:user_key>/', UserDetailView.as_view(), name='user-detail'),

    # Projects
    path('projects/', ProjectListCreateView.as_view(), name='project-list-create'),
    path('projects/<str:project_id>/', ProjectDetailView.as_view(), name='project-detail'),

    # Diagrams under project
    path('projects/<str:project_id>/diagrams/', DiagramListCreateView.as_view(), name='diagram-list-create'),
    path('projects/<str:project_id>/diagrams/<str:diagram_id>/', DiagramDetailView.as_view(), name='diagram-detail'),

    # Components under diagram
    path('projects/<str:project_id>/diagrams/<str:diagram_id>/components/',
         ComponentListCreateUnderDiagramView.as_view(), name='component-list-create'),
    path('projects/<str:project_id>/diagrams/<str:diagram_id>/components/<str:component_id>/',
        ComponentDetailUnderDiagramView.as_view(), name='component-detail'),
    
    # Threats under diagram
    path('projects/<str:project_id>/diagrams/<str:diagram_id>/threats/',
         ThreatListCreateView.as_view(), name='threat-list-create'),
    path('projects/<str:project_id>/diagrams/<str:diagram_id>/threats/<str:threat_id>/',
        ThreatDetailView.as_view(), name='threat-detail'),
    
    # Trust boundaries under diagram
    path('projects/<str:project_id>/diagrams/<str:diagram_id>/trust-boundaries/',
         TrustBoundaryListCreateView.as_view(), name='trust-boundary-list-create'),
    path('projects/<str:project_id>/diagrams/<str:diagram_id>/trust-boundaries/<str:boundary_id>/',
        TrustBoundaryDetailView.as_view(), name='trust-boundary-detail'),
    
    path("projects/<str:project_id>/diagrams/<str:diagram_id>/sync",
        DiagramBulkSyncView.as_view(),
        name="diagram-bulk-sync"),
    
    # Threat Assessment
    path("projects/<str:project_id>/diagrams/<str:diagram_id>/assess-threats",
        ThreatAssessmentView.as_view(),
        name="threat-assessment"),
]

urlpatterns += [
    re_path(
        r"^api/projects/(?P<project_id>[^/]+)/diagrams/(?P<diagram_id>[^/]+)/sync/?$",
        DiagramBulkSyncView.as_view(),
        name="diagram-bulk-sync",
    ),
]
