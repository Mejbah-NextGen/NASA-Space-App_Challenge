# Roles and permissions

## Public visitor

Can view the homepage, weather, historical explorer, crop insights, data sources, methodology, published learning resources, help, contact, privacy, and terms. Public pages never expose private farms, users, consultation threads, or unreviewed content.

## Farmer

Can:

- manage only their own farms, fields, crop records, activities, and tasks;
- run/save only scenarios tied to their farms;
- create/view/update only their decision journal and outcomes;
- browse approved Agriculturalists;
- create consultations and choose which owned Farm to share;
- participate only in their own consultation threads;
- revoke active Farm-data consent and close their own consultation;
- read only their own notifications and AI conversations.

Another Farmer’s object is excluded from the queryset before lookup. The result is a 404 instead of confirmation that the private object exists.

## Agriculturalist

Public signup creates a pending professional application. Verified expert functionality requires both:

1. `AgriculturalistProfile.is_approved=True`
2. an Admin-recorded approval workflow

An approved Agriculturalist can view only assigned cases and Farmer context covered by that case’s active consent. They may reply, create recommendations, update allowed consultation state, and draft/submit learning resources. They cannot search arbitrary private Farms or unassigned Farmer records.

## Platform Admin

Admin accounts are provisioned securely; no public Admin registration exists. Admins can:

- view/search accounts and activate/suspend users;
- approve/reject/request more information from Agriculturalists;
- inspect aggregate Farm and consultation metrics;
- register datasets and run validated imports;
- review learning content;
- inspect integration status and audit records;
- export sanitized account reports.

The custom platform dashboard is the primary Admin experience. `/django-admin/` remains separate for authorized technical administration.

## Enforcement map

- `FarmerRequiredMixin`: authenticated Farmer only.
- `AgriculturalistRequiredMixin`: authenticated Agriculturalist with approved profile.
- `PlatformAdminRequiredMixin`: authenticated Admin only.
- Owner-filtered querysets: Farm, Field, Planting, Simulation, Decision, Consultation, Notification, AI Conversation.
- Assignment/consent filters: Agriculturalist case and shared Farm access.
- Model `clean()` methods: cross-object integrity.
- CSRF + POST-only views: logout, archive, state changes, messages, read actions, approvals.

Navigation is adjusted for usability, but hidden links are never treated as authorization.

## Sensitive actions

- User role is absent from profile/settings forms.
- Admin cannot suspend the current Admin session through the custom action.
- Demo accounts are accepted only in explicit development mode.
- Password changes use Django’s secure flow and retain the signed-in session appropriately.
- Password-reset links are time-limited and signed. Signup verification links use the same protection when `EMAIL_VERIFICATION_ENABLED=true`; the feature is temporarily disabled by default.
- Uploaded images and CSVs have limits and validation.
- Report cells beginning with spreadsheet formula characters are escaped.
- Audit metadata excludes recognized secret keys.
