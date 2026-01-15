#!/usr/bin/env python3
"""
Parameter Store Management Script
Helps create, read, update, and delete parameters in AWS Parameter Store.
"""

import sys
import argparse
import json
from src.services.parameter_store_service import ParameterStoreService


def create_parameter(args):
    """Create a new parameter in Parameter Store."""
    print(f"Creating parameter: {args.name}")
    
    ParameterStoreService.put_parameter(
        param_name=args.name,
        param_value=args.value,
        param_type=args.type,
        description=args.description or '',
        overwrite=args.overwrite
    )
    
    print(f"✅ Successfully created parameter: {args.name}")


def get_parameter(args):
    """Get a parameter value from Parameter Store."""
    print(f"Fetching parameter: {args.name}")
    
    try:
        value = ParameterStoreService.get_parameter(
            param_name=args.name,
            with_decryption=args.decrypt
        )
        
        if args.show_value:
            print(f"\n{args.name} = {value}\n")
        else:
            print(f"\n{args.name} = {'*' * min(len(value), 20)}\n")
            print("(Use --show-value to display the actual value)")
    
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def get_parameters_by_path(args):
    """Get multiple parameters by path."""
    print(f"Fetching parameters from path: {args.path}")
    
    try:
        parameters = ParameterStoreService.get_parameters_by_path(
            path=args.path,
            with_decryption=args.decrypt,
            recursive=args.recursive
        )
        
        print(f"\nFound {len(parameters)} parameters:\n")
        
        for name, value in parameters.items():
            if args.show_value:
                print(f"  {name} = {value}")
            else:
                print(f"  {name} = {'*' * min(len(value), 20)}")
        
        if not args.show_value:
            print("\n(Use --show-value to display actual values)")
    
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def delete_parameter(args):
    """Delete a parameter from Parameter Store."""
    if not args.force:
        confirm = input(f"Are you sure you want to delete '{args.name}'? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
    
    print(f"Deleting parameter: {args.name}")
    
    try:
        ParameterStoreService.delete_parameter(param_name=args.name)
        print(f"✅ Successfully deleted parameter: {args.name}")
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def setup_environment(args):
    """Set up parameters for a specific environment."""
    env = args.env.upper()
    prefix = args.prefix
    
    print(f"Setting up parameters for {env} environment...")
    print(f"Prefix: {prefix}")
    print()
    
    # Elasticsearch parameters
    print("📊 Elasticsearch Configuration:")
    es_password = input(f"  ES Password [{env}]: ")
    es_username = input(f"  ES Username [{env}] (optional, press Enter to skip): ")
    es_api_key = input(f"  ES API Key [{env}] (optional, press Enter to skip): ")
    
    if es_password:
        ParameterStoreService.put_parameter(
            f"{prefix}/{env}/ELASTICSEARCH/PASSWORD",
            es_password,
            "SecureString",
            f"Elasticsearch password for {env}",
            overwrite=True
        )
        print(f"  ✅ Created {prefix}/{env}/ELASTICSEARCH/PASSWORD")
    
    if es_username:
        ParameterStoreService.put_parameter(
            f"{prefix}/{env}/ELASTICSEARCH/USERNAME",
            es_username,
            "String",
            f"Elasticsearch username for {env}",
            overwrite=True
        )
        print(f"  ✅ Created {prefix}/{env}/ELASTICSEARCH/USERNAME")
    
    if es_api_key:
        ParameterStoreService.put_parameter(
            f"{prefix}/{env}/ELASTICSEARCH/API_KEY",
            es_api_key,
            "SecureString",
            f"Elasticsearch API key for {env}",
            overwrite=True
        )
        print(f"  ✅ Created {prefix}/{env}/ELASTICSEARCH/API_KEY")
    
    print()
    
    # MySQL parameters
    print("🗄️  MySQL Configuration:")
    mysql_password = input(f"  MySQL Password [{env}]: ")
    mysql_user = input(f"  MySQL User [{env}] (optional, press Enter to skip): ")
    mysql_host = input(f"  MySQL Host [{env}] (optional, press Enter to skip): ")
    
    if mysql_password:
        ParameterStoreService.put_parameter(
            f"{prefix}/{env}/MYSQL/PASSWORD",
            mysql_password,
            "SecureString",
            f"MySQL password for {env}",
            overwrite=True
        )
        print(f"  ✅ Created {prefix}/{env}/MYSQL/PASSWORD")
    
    if mysql_user:
        ParameterStoreService.put_parameter(
            f"{prefix}/{env}/MYSQL/USER",
            mysql_user,
            "String",
            f"MySQL user for {env}",
            overwrite=True
        )
        print(f"  ✅ Created {prefix}/{env}/MYSQL/USER")
    
    if mysql_host:
        ParameterStoreService.put_parameter(
            f"{prefix}/{env}/MYSQL/HOST",
            mysql_host,
            "String",
            f"MySQL host for {env}",
            overwrite=True
        )
        print(f"  ✅ Created {prefix}/{env}/MYSQL/HOST")
    
    print()
    print(f"✅ Environment setup complete for {env}!")
    print()
    print("To use these parameters, set in your environment:")
    print(f"  ENV={env}")
    print(f"  USE_PARAMETER_STORE=true")
    print(f"  PARAMETER_STORE_PREFIX={prefix}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage AWS Parameter Store parameters for ElasMetrics"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create parameter
    create_parser = subparsers.add_parser('create', help='Create a new parameter')
    create_parser.add_argument('name', help='Parameter name (e.g., /ELASMETRICS/STAGING/MYSQL/PASSWORD)')
    create_parser.add_argument('value', help='Parameter value')
    create_parser.add_argument('--type', choices=['String', 'StringList', 'SecureString'],
                               default='SecureString', help='Parameter type')
    create_parser.add_argument('--description', help='Parameter description')
    create_parser.add_argument('--overwrite', action='store_true', help='Overwrite if exists')
    
    # Get parameter
    get_parser = subparsers.add_parser('get', help='Get a parameter value')
    get_parser.add_argument('name', help='Parameter name')
    get_parser.add_argument('--no-decrypt', dest='decrypt', action='store_false',
                           help='Do not decrypt SecureString parameters')
    get_parser.add_argument('--show-value', action='store_true',
                           help='Show actual value (default: masked)')
    
    # Get parameters by path
    list_parser = subparsers.add_parser('list', help='List parameters by path')
    list_parser.add_argument('path', help='Parameter path (e.g., /ELASMETRICS/STAGING/)')
    list_parser.add_argument('--recursive', action='store_true', help='Recursive search')
    list_parser.add_argument('--no-decrypt', dest='decrypt', action='store_false',
                            help='Do not decrypt SecureString parameters')
    list_parser.add_argument('--show-value', action='store_true',
                            help='Show actual values (default: masked)')
    
    # Delete parameter
    delete_parser = subparsers.add_parser('delete', help='Delete a parameter')
    delete_parser.add_argument('name', help='Parameter name')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Setup environment
    setup_parser = subparsers.add_parser('setup', help='Setup parameters for an environment')
    setup_parser.add_argument('env', choices=['STAGING', 'PRODUCTION', 'DEV'],
                             help='Environment name')
    setup_parser.add_argument('--prefix', default='/ELASMETRICS',
                             help='Parameter prefix (default: /ELASMETRICS)')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'create':
            create_parameter(args)
        elif args.command == 'get':
            get_parameter(args)
        elif args.command == 'list':
            get_parameters_by_path(args)
        elif args.command == 'delete':
            delete_parameter(args)
        elif args.command == 'setup':
            setup_environment(args)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

