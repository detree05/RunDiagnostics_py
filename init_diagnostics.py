#!/usr/bin/env python3
# coding: utf-8
import argparse
import sys
import re
import yaml
from invoke import UnexpectedExit
from fabric import Connection, Config, transfer

COMMANDS_YAML_FILE = "diagnostics.yaml"

class Color:
    green = '\033[92m'
    yellow = '\033[33m'
    red = '\033[91m'
    bold = '\033[1m'
    underline = '\033[4m'
    end = '\033[0m'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--creds", type=str, required=True, help="Credentials, must have form of 'username:password@ip_address'")
    parser.add_argument("--debug", action='store_true', help="Debug mode")
    return parser.parse_args()

def init_credentials(args):
    credentials = args.creds
    if not re.match(r".+:.+\@.+", credentials):
        print(f"{Color.red}[!] Данные должны иметь вид username:password@ip_address{Color.end}")
        sys.exit(1)
    credentials = re.split(":|@", credentials)
    username = credentials[0]
    password = credentials[1]
    ip_address = credentials[2]
    return ip_address, username, password

def init_commands_list():
    try:
        stream = open(COMMANDS_YAML_FILE, 'r')
        commands_list = yaml.safe_load(stream)
    except Exception as e:
        print(f"{Color.red}[!] Не удалось получить список команд из {COMMANDS_YAML_FILE}. {e}{Color.end}")
        sys.exit(1)
    return commands_list

def run_command_block(ssh_con, command_block, debug_state):
    print(f"{Color.green}\n[-] Блок {command_block["block"]} -- commands -- {command_block["description"]}{Color.end}")
    for cmd in command_block["commands"]:
        if debug_state:
            print(f"{Color.yellow}[~] {cmd}{Color.end}")
        try:
            result = ssh_con.run(cmd, hide=True)
            if not result.stdout:
                print(f"[.] Результат отсутствует.")
            else:
                print(f"[.] {result.stdout.strip()}")
        except KeyboardInterrupt:
            sys.exit(1)
        except UnexpectedExit as e:
            print(f"{Color.red}[!] Блок {command_block["block"]}, command [{cmd}] провалился в исполнении. {e.result.stderr}{Color.end}")
        except Exception as e:
            print(f"{Color.red}[!] Блок {command_block["block"]}, script [{cmd}] провалился в исполнении. {e}{Color.end}")
            sys.exit(1)

def run_script_block(ssh_con, script_block, debug_state):
    print(f"{Color.green}[-] Блок {script_block["block"]} -- scripts -- {script_block["description"]}{Color.end}")
    for script in script_block["scripts"]:
        if debug_state:
            print(f"{Color.yellow}[~] {script}{Color.end}")
        try:
            scp_con = transfer.Transfer(ssh_con)
            scp_con.put(f"./scripts/{script}")
            ssh_con.run(f"chmod +x ~/{script}", hide=True)
            result = ssh_con.run(f"~/{script}", hide=True)
            if not result.stdout:
                print(f"[.] Результат отсутствует.")
            else:
                print(f"[.] {result.stdout.strip()}")
        except KeyboardInterrupt:
            sys.exit(1)
        except UnexpectedExit as e:
            print(f"{Color.red}[!] Блок {script_block["block"]}, script [{script}] провалился в исполнении. {e.result.stderr}{Color.end}")
        except Exception as e:
            print(f"{Color.red}[!] Блок {script_block["block"]}, script [{script}] провалился в исполнении. {e}{Color.end}")
            sys.exit(1)

        ssh_con.run(f"rm -f ~/{script}", hide=True)

def main():
    args = parse_args()
    debug_state = args.debug
    ip_address, username, password = init_credentials(args)
    commands_list = init_commands_list()
    config = Config(overrides={'sudo': {'password': password}, 'connect_kwargs': {'password': password}})
    ssh_con = Connection(f"{username}@{ip_address}", config=config)
    for block in commands_list:
        if "commands" in block:
            run_command_block(ssh_con, block, debug_state)
        if "scripts" in block:
            run_script_block(ssh_con, block, debug_state)

if __name__ == "__main__":
    main()