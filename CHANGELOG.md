# Changelog

All notable changes to the Battery Aggregator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-28

### Added
- Initial release of Battery Aggregator for Victron Venus OS
- Multi-battery BMS aggregation (SOC, voltage, current, temperature)
- Conservative SOC selection (uses lowest value)
- Voltage averaging across parallel batteries
- Dynamic charge current limiting based on imbalance detection
- Four-tier imbalance protection system (0-5%, 5-10%, 10-15%, >15%)
- BMS internal cell alarm monitoring and propagation
- Automatic service registration on Venus OS via daemontools
- Comprehensive logging to `/var/log/bms-aggregator/current`
- Compatible with ESS (Energy Storage System) mode
- Seamless VE.Bus integration for MultiPlus/Quattro inverters

### Features
- **Imbalance Detection**: Monitors SOC differences between batteries
- **Charge Protection**: Reduces charge current from 100% → 85% → 66% → 33% based on imbalance
- **Cell Alarm Override**: Escalates alarm if BMS detects internal cell issues
- **Real-time Monitoring**: 2-second update interval
- **Persistent Storage**: Configuration survives reboots via `/data` partition
- **Standard Victron Paths**: Publishes all required battery service D-Bus paths
- **Alarm Integration**: Compatible with Victron alarm system

### Documentation
- Comprehensive README with features, compatibility, and usage
- Detailed installation guide (INSTALL.md) with multiple installation methods
- Configuration guide (CONFIGURATION.md) with examples
- Troubleshooting section for common issues

### Tested Configurations
- Hardware: Victron Cerbo GX
- Venus OS: v2.217
- Batteries: 3× SuperB Epsilon V2 150Ah (12V LiFePO4)
- BMS Protocol: CANopen
- Inverter: MultiPlus Compact 12/1200/50-16 (firmware v556)
- ESS Mode: Hub-4 with external battery control

### Known Issues
- Aggregator may not appear immediately in available services (requires systemcalc refresh)
- Device instance 280 may conflict on some systems (requires manual configuration)
- SuperB BMS does not expose raw cell voltages, only alarm flags

### Security
- No external network connections
- Local D-Bus communication only
- Read-only access to BMS services
- Root access required for installation (standard for Venus OS modifications)

## [Unreleased]

### Planned Features
- Web UI for configuration
- Historical imbalance tracking
- Email/push notifications for critical imbalance
- Multi-voltage support (12V/24V/48V auto-detection)
- Support for mixed battery types
- Bluetooth configuration interface
- Integration with Victron VRM Portal widgets

### Under Consideration
- Machine learning for SOC prediction
- Temperature-based charge current adjustment
- Integration with solar forecast for optimal charging
- Battery health scoring system
- Automatic battery matching recommendations

---

## Version History

### Versioning Scheme
- **Major**: Incompatible API changes or major feature additions
- **Minor**: Backwards-compatible functionality additions
- **Patch**: Backwards-compatible bug fixes

### Release Notes Format
Each release includes:
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes

---

## Contributing

To contribute to this changelog:
1. Follow the [Keep a Changelog](https://keepachangelog.com/) format
2. Add unreleased changes under `[Unreleased]` section
3. Move to versioned section upon release
4. Include date in YYYY-MM-DD format

---

## Support

For issues or feature requests, please visit:
- GitHub Issues: https://github.com/drurew/Battery-Aggregator/issues
- Victron Community: https://community.victronenergy.com/

## [1.1.0] - 2025-12-28

### Added
- **Configuration File Support**: New `config.ini` file allows customization of all thresholds and parameters without modifying Python code
- Configurable imbalance thresholds (OK, Warning, Alarm levels)
- Configurable charge current limits (nominal and reduced)
- Configurable battery parameters (capacity, voltages, discharge current)
- Configurable BMS service names and device instance
- Configurable update interval and debug logging
- Default configuration values embedded in code (works without config file)

### Changed
- **Increased default warning threshold from 10% to 15%** - Better suited for battery banks with mixed charge/discharge characteristics
- **Increased default alarm threshold to 20%** (was implicitly >15%)
- Firmware version updated to 1.1.0
- Charge current calculation now uses configured thresholds from config file
- Service logs configuration values on startup for transparency
- Update interval now configurable (default still 2.0 seconds)

### Technical Details
- Uses Python's `configparser` for INI file parsing
- Config file location: `/data/bms_aggregator/config.ini`
- Falls back to embedded defaults if config file missing or invalid
- All numeric values validated through ConfigParser type conversion
- Config changes require service restart: `svc -t /service/bms-aggregator`

### Rationale
This update addresses scenarios where one battery in a parallel bank has different charge/discharge characteristics than the others. In such cases, the SOC imbalance will persist or increase during charging, not equalize. The increased thresholds (15% warning, 20% alarm) prevent constant warnings while still providing protection against severe imbalance.

### Migration from v1.0.0
Existing installations will continue working with embedded defaults. To customize:
1. Copy `config.ini` to `/data/bms_aggregator/` on Cerbo GX
2. Edit values as needed
3. Restart service: `svc -t /service/bms-aggregator`

