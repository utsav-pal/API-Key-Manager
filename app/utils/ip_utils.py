"""
IP validation utilities.
"""
import ipaddress
from typing import List, Optional


def is_ip_allowed(client_ip: str, allowed_ips: Optional[List[str]]) -> bool:
    """
    Check if client IP is allowed based on whitelist.
    
    Args:
        client_ip: The client's IP address
        allowed_ips: List of allowed IPs/CIDRs, or None/empty for no restriction
        
    Returns:
        bool: True if allowed, False otherwise
    """
    # If no allowed_ips set, allow all
    if not allowed_ips:
        return True
    
    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        # Invalid IP address format
        return False
    
    for allowed in allowed_ips:
        try:
            # Check if it's a network (CIDR notation)
            if "/" in allowed:
                network = ipaddress.ip_network(allowed, strict=False)
                if client_addr in network:
                    return True
            else:
                # Single IP address
                if client_addr == ipaddress.ip_address(allowed):
                    return True
        except ValueError:
            # Invalid network/IP in whitelist, skip
            continue
    
    return False
