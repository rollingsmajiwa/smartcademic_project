from django.db import models

# ParentProfile is defined in admin_app.models and synced to UserProfile.role
# via post_save signals so there is a single source of truth across the project.