#!/usr/bin/env python3
"""
Docker Configuration Verification Script
Verifies that all Docker-related files are properly configured
"""

import os
import sys
from pathlib import Path


def check_file_exists(filepath, description):
    """Check if a file exists"""
    if Path(filepath).exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ Missing {description}: {filepath}")
        return False


def check_dockerfile():
    """Verify Dockerfile exists and has required content"""
    print("\n[Dockerfile Verification]")
    if not check_file_exists("Dockerfile", "Dockerfile"):
        return False

    with open("Dockerfile", "r") as f:
        content = f.read()

    checks = {
        "FROM python:3.10-slim": "Base image specified",
        "WORKDIR /app": "Working directory set",
        "COPY requirements.txt": "Requirements copied",
        "pip install": "Dependencies installation",
        "COPY app/": "Application code copied",
        "EXPOSE 8000": "Port exposed",
        "CMD": "Startup command defined",
        "useradd": "Non-root user created",
    }

    all_passed = True
    for check, description in checks.items():
        if check in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ Missing: {description}")
            all_passed = False

    return all_passed


def check_docker_compose():
    """Verify docker-compose files"""
    print("\n[Docker Compose Verification]")

    files = {
        "docker-compose.yml": "Production configuration",
        "docker-compose.dev.yml": "Development configuration",
    }

    all_passed = True
    for filepath, description in files.items():
        if check_file_exists(filepath, description):
            with open(filepath, "r") as f:
                content = f.read()

            required = [
                "version:",
                "services:",
                "app:",
                "build:",
                "ports:",
                "environment:",
            ]
            for req in required:
                if req in content:
                    print(f"    ✓ Contains {req}")
                else:
                    print(f"    ✗ Missing {req}")
                    all_passed = False
        else:
            all_passed = False

    return all_passed


def check_dockerignore():
    """Verify .dockerignore file"""
    print("\n[.dockerignore Verification]")

    if not check_file_exists(".dockerignore", ".dockerignore"):
        return False

    with open(".dockerignore", "r") as f:
        content = f.read()

    important_ignores = ["venv/", "__pycache__/", ".git/", "*.pyc", ".env"]

    all_passed = True
    for ignore in important_ignores:
        if ignore in content:
            print(f"  ✓ Ignores {ignore}")
        else:
            print(f"  ⚠ Should ignore {ignore}")
            all_passed = False

    return all_passed


def check_makefile():
    """Verify Makefile"""
    print("\n[Makefile Verification]")

    if not check_file_exists("Makefile", "Makefile"):
        print("  ⚠ Makefile is optional but recommended")
        return True

    with open("Makefile", "r") as f:
        content = f.read()

    commands = ["build", "up", "down", "logs", "shell", "test", "clean"]

    for cmd in commands:
        if f"{cmd}:" in content:
            print(f"  ✓ Has '{cmd}' command")
        else:
            print(f"  ⚠ Missing '{cmd}' command")

    return True


def check_scripts():
    """Verify helper scripts"""
    print("\n[Scripts Verification]")

    scripts = {
        "docker-build.sh": "Docker build script",
        "start.sh": "Local start script",
    }

    for script, description in scripts.items():
        if Path(script).exists():
            print(f"✓ {description}: {script}")
            # Check if executable
            if os.access(script, os.X_OK):
                print("    ✓ Executable")
            else:
                print(f"    ⚠ Not executable (run: chmod +x {script})")
        else:
            print(f"⚠ Optional {description} missing: {script}")

    return True


def check_env_files():
    """Verify environment configuration files"""
    print("\n[Environment Files Verification]")

    if not check_file_exists(".env.example", ".env.example template"):
        return False

    with open(".env.example", "r") as f:
        content = f.read()

    required_vars = ["HOSPITAL_API_BASE_URL", "MAX_CSV_ROWS", "PORT"]

    all_passed = True
    for var in required_vars:
        if var in content:
            print(f"  ✓ Has {var}")
        else:
            print(f"  ✗ Missing {var}")
            all_passed = False

    if Path(".env").exists():
        print("  ✓ .env file exists")
    else:
        print("  ⚠ .env file not found (will use .env.example in Docker)")

    return all_passed


def check_application_files():
    """Verify application files are present"""
    print("\n[Application Files Verification]")

    files = {
        "app/__init__.py": "App package init",
        "app/main.py": "Main application",
        "app/models.py": "Data models",
        "app/services.py": "Business logic",
        "app/utils.py": "Utilities",
        "requirements.txt": "Dependencies",
    }

    all_passed = True
    for filepath, description in files.items():
        if not check_file_exists(filepath, description):
            all_passed = False

    return all_passed


def check_docker_documentation():
    """Verify Docker documentation"""
    print("\n[Documentation Verification]")

    docs = {"README.md": "Main documentation", "DOCKER.md": "Docker-specific guide"}

    for filepath, description in docs.items():
        if Path(filepath).exists():
            print(f"✓ {description}: {filepath}")
            with open(filepath, "r") as f:
                content = f.read()
                if "docker" in content.lower():
                    print("    ✓ Contains Docker instructions")
        else:
            if filepath == "DOCKER.md":
                print(f"⚠ Optional {description} missing")
            else:
                print(f"✗ Missing {description}")

    return True


def print_docker_commands():
    """Print useful Docker commands"""
    print("\n" + "=" * 70)
    print("DOCKER QUICK REFERENCE")
    print("=" * 70)
    print("\n📦 Build & Run:")
    print("  docker-compose build                 # Build the image")
    print("  docker-compose up                    # Start (foreground)")
    print("  docker-compose up -d                 # Start (background)")
    print("  docker-compose down                  # Stop containers")

    print("\n🔧 Development:")
    print("  docker-compose -f docker-compose.dev.yml up    # Dev mode")
    print("  docker-compose exec app /bin/bash              # Shell access")
    print("  docker-compose logs -f                         # View logs")

    print("\n🧪 Testing:")
    print("  docker-compose exec app python test_setup.py   # Run tests")
    print("  curl -X POST http://localhost:8000/hospitals/bulk \\")
    print("       -F 'file=@sample_hospitals.csv'            # Test upload")

    print("\n📊 Monitoring:")
    print("  docker-compose ps                    # Container status")
    print("  docker stats hospital-bulk-processor # Resource usage")
    print("  curl http://localhost:8000/health    # Health check")

    if Path("Makefile").exists():
        print("\n⚡ Make Commands (easier):")
        print("  make build      # Build image")
        print("  make up         # Start (production)")
        print("  make dev        # Start (development)")
        print("  make logs       # View logs")
        print("  make shell      # Open shell")
        print("  make test       # Run tests")
        print("  make down       # Stop")
        print("  make clean      # Clean up")

    print("\n🌐 Access Points:")
    print("  API:          http://localhost:8000")
    print("  Swagger UI:   http://localhost:8000/docs")
    print("  ReDoc:        http://localhost:8000/redoc")
    print("  Health:       http://localhost:8000/health")
    print()


def main():
    """Main verification process"""
    print("=" * 70)
    print("DOCKER CONFIGURATION VERIFICATION")
    print("=" * 70)

    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    checks = [
        ("Application Files", check_application_files),
        ("Dockerfile", check_dockerfile),
        ("Docker Compose", check_docker_compose),
        (".dockerignore", check_dockerignore),
        ("Environment Files", check_env_files),
        ("Makefile", check_makefile),
        ("Scripts", check_scripts),
        ("Documentation", check_docker_documentation),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ Error checking {name}: {str(e)}")
            results[name] = False

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! Docker configuration is ready.")
        print_docker_commands()
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
