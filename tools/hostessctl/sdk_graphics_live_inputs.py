"""Local input qualification for one finite live owner; creates no process."""
from copy import deepcopy
import os
from pathlib import Path
import sys

from tools.hostessctl.sdk_graphics_batch import load_baseline, load_batch, read_json
from tools.hostessctl.immutable_input_binding import WindowsInputBinding
from tools.hostessctl.sdk_graphics_live_contract import load_config, project_settings, project_status, sha_file


class LiveInputs:
    def __init__(self, config_path, catalog, batch_paths=()):
        self.binding = None
        self.batches = {}
        self.config_path, self.catalog = Path(config_path), Path(catalog)
        probe = None
        try:
            # Preserve v1/rehash path semantics (including unsupported strong
            # binding namespaces). Only an explicit immutable selection opens
            # Windows handles, then re-reads and joins the bootstrap bytes.
            bootstrap = read_json(Path(config_path))
            immutable = bootstrap.get("input_binding") == "windows-immutable"
            if immutable:
                self.binding = WindowsInputBinding()
                if self.binding.read_json(config_path) != bootstrap:
                    raise ValueError("immutable_bootstrap_changed")
                if len(batch_paths) != 2:
                    raise ValueError("immutable_complete_batch_selection_required")
            self.config = load_config(config_path, hash_file=self.hash_file, document=self.document)
            self.config_digest = self.hash_file(config_path)
            load_baseline(self.catalog, **self.readers())
            if self.hash_file(self.catalog) != self.config["catalog_sha256"]:
                raise ValueError("catalog_pin_changed")
            self.reference = project_status(self.document(Path(self.config["app_status_reference"]["path"])), self.config)
            self.settings = project_settings(self.document(Path(self.config["settings_reference"]["path"])))
            if self.binding:
                self.binding.add(sys.executable)
                for path in batch_paths:
                    key = self.binding.key(path)
                    if key in self.batches:
                        raise ValueError("distinct_immutable_batches_required")
                    self.batches[key] = load_batch(Path(path), self.catalog, **self.readers())
                self.binding.assert_current()
        except BaseException as error:
            for binding in (probe, self.binding):
                if binding is not None:
                    try:
                        binding.close()
                    except OSError:
                        # Preserve ownership for the exceptional caller to retire.
                        error.sdk_graphics_input_binding = binding
            raise

    def hash_file(self, path):
        return self.binding.sha_file(path) if self.binding else sha_file(path)

    def document(self, path):
        return self.binding.read_json(path) if self.binding else read_json(Path(path))

    def readers(self):
        return {"read": self.binding.read_file, "document": self.binding.read_json} if self.binding else {}

    def batch(self, path):
        if not self.binding:
            return load_batch(Path(path), self.catalog)
        self.binding.assert_current()
        key = self.binding.key(path)
        if key not in self.batches:
            raise ValueError("original_immutable_batch_required")
        return deepcopy(self.batches[key])

    def assert_current(self, config):
        if config != self.config:
            raise ValueError("retained_live_config_changed")
        if self.binding:
            self.binding.assert_current()
        else:
            if sha_file(self.config_path) != self.config_digest:
                raise ValueError("live_input_changed")
            load_config(self.config_path)
            if sha_file(self.catalog) != self.config["catalog_sha256"]:
                raise ValueError("catalog_pin_changed")

    def report(self):
        return self.binding.report() if self.binding else {"mode": "rehash", "released": True}

    def close(self):
        if self.binding:
            self.binding.close()
