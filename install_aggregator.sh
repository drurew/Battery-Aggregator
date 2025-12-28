#!/bin/bash
# Install BMS Aggregator Service on Victron Cerbo GX (Venus OS)

set -e

echo "========================================="
echo "BMS Aggregator Service Installer"
echo "========================================="

# Check if running on Cerbo
if [ ! -d "/opt/victronenergy" ]; then
    echo "ERROR: This script must be run on a Victron Cerbo GX"
    exit 1
fi

echo "Creating installation directory..."
mkdir -p /data/bms_aggregator

echo "Copying service files..."
cp bms_aggregator.py /data/bms_aggregator/
chmod +x /data/bms_aggregator/bms_aggregator.py

echo "Creating service directory for Venus OS..."
mkdir -p /service/bms-aggregator

echo "Creating run script..."
cat > /service/bms-aggregator/run <<'EOF'
#!/bin/sh
exec 2>&1
exec /usr/bin/python3 /data/bms_aggregator/bms_aggregator.py
EOF

chmod +x /service/bms-aggregator/run

echo "Creating log directory..."
mkdir -p /service/bms-aggregator/log

echo "Creating log run script..."
cat > /service/bms-aggregator/log/run <<'EOF'
#!/bin/sh
exec multilog t /var/log/bms-aggregator
EOF

chmod +x /service/bms-aggregator/log/run
mkdir -p /var/log/bms-aggregator

echo "Waiting for service to start (daemontools picks it up automatically)..."
sleep 5

echo ""
echo "Checking if service is running..."
if svstat /service/bms-aggregator 2>/dev/null; then
    echo "Service is running!"
else
    echo "Starting service manually..."
    svc -u /service/bms-aggregator
    sleep 3
    svstat /service/bms-aggregator || echo "Service not yet detected"
fi

echo ""
echo "========================================="
echo "Installation complete!"
echo "========================================="
echo ""
echo "The aggregator service should be running."
echo ""
echo "To set it as the active battery service, run:"
echo ""
echo "  dbus -y com.victronenergy.settings /Settings/SystemSetup/BatteryService SetValue 'com.victronenergy.battery.bms_aggregator'"
echo ""
echo "To check logs:"
echo "  tail -f /var/log/bms-aggregator/current"
echo ""
echo "To check if it's visible on D-Bus:"
echo "  dbus -y com.victronenergy.battery.bms_aggregator /Soc GetValue"
echo ""
echo "Service control commands:"
echo "  svstat /service/bms-aggregator   # Check status"
echo "  svc -d /service/bms-aggregator   # Stop"
echo "  svc -u /service/bms-aggregator   # Start"
echo "  svc -t /service/bms-aggregator   # Restart"
echo ""
