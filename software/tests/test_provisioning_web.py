from smartblaster.provisioning.service import ProvisioningService
from smartblaster.provisioning.web import create_provisioning_app


def test_create_provisioning_app() -> None:
    app = create_provisioning_app(ProvisioningService())
    assert app.title == "SmartBlaster Provisioning"
