# SmartBlaster Tests

Run from the software directory:

```bash
pytest
```

Current coverage:
- `test_config.py` for configuration defaults
- `test_state_machine.py` for baseline HVAC state transitions
- `test_midea_command.py` for Midea command validation
- `test_esp32_schema.py` for command/ack contract parser helpers
- `test_ir_transport.py` for bridge transport and ack handling
- `test_cli.py` for CLI argument parsing and command building
