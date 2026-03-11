#!/usr/bin/env python3
from __future__ import annotations

import getpass
import re

from telethon.network import connection
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

try:
    from python_socks import ProxyType
except Exception:
    ProxyType = None


def prompt_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("This field is required.")


def prompt_api_id() -> int:
    while True:
        raw_value = prompt_non_empty("Telegram API ID: ")
        try:
            return int(raw_value)
        except ValueError:
            print("API ID must be an integer.")


def prompt_code() -> str:
    return prompt_non_empty("Please enter the code you received: ")


def prompt_password() -> str:
    while True:
        password = getpass.getpass("Two-step verification password: ").strip()
        if password:
            return password
        print("This field is required.")


def normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-()]", "", phone.strip())


def prompt_phone() -> str:
    pattern = re.compile(r"^\+[1-9]\d{1,14}$")
    while True:
        raw_phone = prompt_non_empty("Phone number (international format): ")
        phone = normalize_phone(raw_phone)
        if pattern.fullmatch(phone):
            return phone
        print(
            "Phone number must be in international format with a leading +, "
            "e.g. +8613800138000."
        )


def prompt_optional(prompt: str) -> str:
    return input(prompt).strip()


def prompt_proxy_port() -> int:
    while True:
        raw_value = prompt_non_empty("Proxy port: ")
        try:
            port = int(raw_value)
        except ValueError:
            print("Proxy port must be an integer.")
            continue
        if 1 <= port <= 65535:
            return port
        print("Proxy port must be between 1 and 65535.")


def prompt_proxy_config() -> dict:
    proxy_type = prompt_optional(
        "Proxy type (leave empty/direct, socks5, socks4, http, mtproto): "
    ).lower()
    if proxy_type == "":
        return {}
    if proxy_type == "mtproxy":
        proxy_type = "mtproto"
    if proxy_type not in {"socks5", "socks4", "http", "mtproto"}:
        raise ValueError("Unsupported proxy type.")

    proxy_host = prompt_non_empty("Proxy host: ")
    proxy_port = prompt_proxy_port()

    if proxy_type == "mtproto":
        proxy_secret = prompt_non_empty("MTProto secret: ")
        mtproto_connection = getattr(
            connection, "ConnectionTcpMTProxyRandomizedIntermediate", None
        ) or getattr(connection, "ConnectionTcpMTProxyIntermediate", None)
        if mtproto_connection is None:
            raise RuntimeError(
                "Current Telethon version does not provide MTProto proxy support."
            )
        return {
            "connection": mtproto_connection,
            "proxy": (proxy_host, proxy_port, proxy_secret),
        }

    if ProxyType is None:
        raise RuntimeError("python-socks is required for SOCKS/HTTP proxy support.")

    proxy_username = prompt_optional("Proxy username (optional): ")
    proxy_password = (
        getpass.getpass("Proxy password (optional): ")
        if proxy_username
        else prompt_optional("Proxy password (optional): ")
    )
    proxy_type_map = {
        "socks5": ProxyType.SOCKS5,
        "socks4": ProxyType.SOCKS4,
        "http": ProxyType.HTTP,
    }
    return {
        "proxy": (
            proxy_type_map[proxy_type],
            proxy_host,
            proxy_port,
            True,
            proxy_username or None,
            proxy_password or None,
        )
    }


def run_login_once() -> None:
    api_id = prompt_api_id()
    api_hash = prompt_non_empty("Telegram API hash: ")
    phone = prompt_phone()
    client_kwargs = prompt_proxy_config()

    print("Starting Telegram login flow.")
    print(f"Using phone: {phone}")
    print(
        "Telegram usually delivers the login code inside an existing Telegram app "
        "session from the official 'Telegram' chat, not necessarily via SMS.\n"
    )

    client = TelegramClient(StringSession(), api_id, api_hash, **client_kwargs)
    try:
        client.start(
            phone=lambda: phone,
            code_callback=prompt_code,
            password=prompt_password,
        )

        if not client.is_user_authorized():
            raise RuntimeError("Login did not complete successfully.")

        print("\nStringSession:\n")
        print(client.session.save())
        print(
            "\nCopy the StringSession above into AstrBot's telethon_userbot "
            "adapter config as session_string."
        )
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def main() -> None:
    while True:
        try:
            run_login_once()
            return
        except KeyboardInterrupt:
            print("\nLogin flow cancelled.")
            raise SystemExit(1)
        except Exception as exc:
            print(f"\nLogin flow failed: {exc}")
            print("Restarting from the beginning.\n")


if __name__ == "__main__":
    main()
