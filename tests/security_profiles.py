"""Native tests for the consolidated production configuration."""
from site_profiles import PROFILE_CHECKS, SPA_CHECKS, SITE_CHECKS, run_site_profiles

COMMON_CHECKS = PROFILE_CHECKS + SPA_CHECKS + SITE_CHECKS

def platform_checks(target):
    return ["profile:linux-symlink-denial"] if target.startswith("linux-") else ["profile:windows-link-review-documented"]

def run_profiles(binary, runtime, metadata, target, root, check, done):
    return run_site_profiles(binary, runtime, metadata, target, root, check, done)
