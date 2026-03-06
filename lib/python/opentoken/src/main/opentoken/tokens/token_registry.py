"""
Copyright (c) Truveta. All rights reserved.
"""

import importlib
import pkgutil
from importlib import resources
from typing import Dict, List

from opentoken.attributes.attribute_expression import AttributeExpression
from opentoken.tokens.token import Token


class TokenRegistry:
    @staticmethod
    def load_all_tokens() -> Dict[str, List[AttributeExpression]]:
        definitions: Dict[str, List[AttributeExpression]] = {}

        package_name = "opentoken.tokens.definitions"
        package = importlib.import_module(package_name)

        module_names: List[str] = []
        package_path = getattr(package, "__path__", None)
        if package_path is not None:
            try:
                module_names = [module_info.name for module_info in pkgutil.iter_modules(package_path)]
            except Exception:
                module_names = []

        if not module_names:
            try:
                module_names = [
                    item.name[:-3]
                    for item in resources.files(package).iterdir()
                    if item.name.endswith(".py") and item.name != "__init__.py"
                ]
            except Exception:
                module_names = ["t1_token", "t2_token", "t3_token", "t4_token", "t5_token"]

        for module_name in module_names:
            module = importlib.import_module(f"{package_name}.{module_name}")

            for obj in module.__dict__.values():
                if isinstance(obj, type) and issubclass(obj, Token) and obj is not Token:
                    token = obj()
                    definitions[token.get_identifier()] = token.get_definition()

        return definitions
