"""Rol → izin matrisi (deny-by-default). Kaynak: docs/SOZLESME.md."""

ALL_PERMISSIONS = frozenset(
    {
        "catalog:read", "catalog:manage", "costs:read",
        "lots:read", "lots:receive", "lots:unblock",
        "inventory:read", "inventory:adjust",
        "production:read", "production:manage",
        "butchering:read", "butchering:manage", "butchering:approve_variance",
        "sales:read", "sales:create", "sales:void", "sales:override_price",
        "shipments:read", "shipments:manage",
        "traceability:read",
        "recalls:read", "recalls:manage", "recalls:resolve",
        "ai:read", "ai:run",
        "reports:read", "alerts:read", "alerts:manage",
        "audit:read", "users:manage", "corrections:manage", "documents:manage",
    }
)

_READ = {
    "catalog:read", "lots:read", "inventory:read", "production:read", "butchering:read",
    "sales:read", "shipments:read", "traceability:read", "recalls:read", "reports:read", "alerts:read",
}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "ADMIN": ALL_PERMISSIONS,
    "OPERATOR": frozenset(
        _READ | {"lots:receive", "inventory:adjust", "production:manage", "butchering:manage", "ai:read", "ai:run", "costs:read",
                 "documents:manage"}
    ),
    "SALES": frozenset(
        {"catalog:read", "lots:read", "inventory:read", "sales:read", "sales:create",
         "shipments:read", "shipments:manage", "reports:read"}
    ),
    "TRACEABILITY_MANAGER": frozenset(
        _READ | {"lots:unblock", "recalls:manage", "recalls:resolve", "ai:read", "audit:read", "alerts:manage",
                      "butchering:approve_variance"}
    ),
    "VIEWER": frozenset(_READ | {"ai:read"}),
}

ROLE_NAMES = {
    "ADMIN": "Yönetici",
    "OPERATOR": "Operatör",
    "SALES": "Satış",
    "TRACEABILITY_MANAGER": "İzlenebilirlik Yöneticisi",
    "VIEWER": "Görüntüleyici",
}


def permissions_for(roles: list[str]) -> frozenset[str]:
    out: set[str] = set()
    for r in roles:
        out |= ROLE_PERMISSIONS.get(r, frozenset())
    return frozenset(out)
