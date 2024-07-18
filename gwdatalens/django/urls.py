from gwdatalens.app import app
from gwdatalens.views import render_gwdatalens_tool
from django.urls import path

urlpatterns = [
    path("gwdatalens/", render_gwdatalens_tool, name="gwdatalens"),
]
