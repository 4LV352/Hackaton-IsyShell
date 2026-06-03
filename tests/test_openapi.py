def test_openapi_exposes_isy_token_security_scheme():
    from app.main import app

    spec = app.openapi()

    assert spec["info"]["title"] == "isy-shell-api"
    assert spec["components"]["securitySchemes"]["APIKeyHeader"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-Isy-Token",
    }
    tags = {tag for path in spec["paths"].values() for operation in path.values() for tag in operation.get("tags", [])}
    assert tags == {"Auth", "Clientes", "Execução", "Health", "Logs", "Métricas", "Scripts"}
    assert "/api/v1/info" in spec["paths"]


def test_legacy_entities_module_reexports_current_models():
    from app.models import Script
    from app.models.entities import Script as LegacyScript

    assert LegacyScript is Script
