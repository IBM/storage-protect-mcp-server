## Troubleshooting

### Issue: Python version too old

```bash
# Verify Python version
python3 --version

# If < 3.10, follow Step 1 to install Python 3.11
```

### Issue: pip install fails with "No module named 'hatchling'"

```bash
# Install build dependencies
pip install --upgrade pip setuptools wheel hatchling
pip install -e .
```

### Issue: dsmadmc not found

```bash
# Find dsmadmc
sudo find / -name dsmadmc 2>/dev/null

# Add to PATH
export PATH=$PATH:/path/to/dsmadmc/directory
```

### Issue: Permission denied errors

```bash
# Ensure proper ownership
sudo chown -R $USER:$USER /opt/sp-mcp-server

# Ensure virtual environment is activated
source /opt/sp-mcp-server/venv/bin/activate
```

### Issue: Connection to ISP server fails

```bash
# Test network connectivity
ping your.isp.server.com

# Test dsmadmc directly
dsmadmc -id=admin -password=password -server=your.isp.server.com "query status"

# Check firewall rules
sudo firewall-cmd --list-all
```

