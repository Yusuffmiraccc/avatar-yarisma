"""Route → izin eşlemesi (izin matrisi parity testi ve belge üretimi için)."""

from fastapi.routing import APIRoute

from app.core.config import get_settings
from app.core.deps import get_current_user


def _walk(dep):
    for d in dep.dependencies:
        yield d
        yield from _walk(d)


def _perm(route: APIRoute) -> str | None:
    perm, authed = None, False
    for d in _walk(route.dependant):
        if getattr(d.call, "permission", None):
            perm = d.call.permission
        if d.call is get_current_user:
            authed = True
    return perm or ("AUTHENTICATED" if authed else None)


def route_permissions(app) -> list[tuple[str, str, str | None]]:
    """(method, path, izin | 'AUTHENTICATED' | None=herkese açık). /api/v1 modül router'ları + uygulama kökü."""
    from app.api.v1 import MODULES

    prefix = get_settings().api_v1_prefix
    routes = [(prefix + r.path, r) for m in MODULES for r in m.router.routes if isinstance(r, APIRoute)]
    routes += [(r.path, r) for r in app.routes if isinstance(r, APIRoute)]
    out = []
    for path, r in routes:
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            out.append((m, path, _perm(r)))
    return sorted(out, key=lambda x: (x[1], x[0]))
