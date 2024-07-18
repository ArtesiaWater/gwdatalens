# DataLens as Django Application

## Update urlpatterns

Add to `main/urls.py`:

```python
from gwdatalens.urls import urlpatterns as gwdatalens_urls
from gwdatalens.views import render_gwdatalens_tool

urlpatterns = [
    ...
    path("gwdatalens/", render_gwdatalens_tool, name="gwdatalens"),
]

```