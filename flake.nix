{
  description = "mif-dqf - Data Quality First to be sure about your trading data";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python312;
        
        pythonEnv = python.withPackages (ps: with ps; [
          # Core dependencies
          pandas
          numpy
          pyyaml

          # Optional dependencies
          scipy
          matplotlib
          seaborn
          
          # Dev tools
          pytest
          pytest-cov
          black
          ruff
          isort
          autopep8
          mypy
          ipython
          pip
          virtualenv
          python-dotenv
        ]);
        
        checkIntegrity = pkgs.writeShellScriptBin "check-integrity" ''
          #!/usr/bin/env bash
          set -euo pipefail
          
          REQUIRED=("flake.nix" "flake.lock" ".envrc" ".gitignore" "justfile")
          MISSING=()
          for f in "''${REQUIRED[@]}"; do
            [ ! -f "$f" ] && MISSING+=("$f")
          done
          
          if [ ''${#MISSING[@]} -gt 0 ]; then
            echo "❌ Fichiers manquants: ''${MISSING[@]}"
            return 1
          fi
          echo "✅ Intégrité OK"
        '';
        
        setupVenv = pkgs.writeShellScriptBin "setup-venv" ''
          #!/usr/bin/env bash
          set -euo pipefail
          
          VENV_DIR=".venv"
          if [ ! -d "$VENV_DIR" ]; then
            ${python}/bin/python -m venv "$VENV_DIR" --system-site-packages
          fi
          
          source "$VENV_DIR/bin/activate"
          pip install --upgrade pip setuptools wheel --quiet
          [ -f "requirements.txt" ] && pip install -r requirements.txt --quiet
          echo "✅ Venv prêt"
        '';
        
        autoFormat = pkgs.writeShellScriptBin "auto-format" ''
          #!/usr/bin/env bash
          set -euo pipefail
          
          ${pythonEnv}/bin/ruff check . --select F841 --fix --unsafe-fixes --quiet || true
          ${pythonEnv}/bin/isort . --profile black --quiet || true
          ${pythonEnv}/bin/black . --quiet || true
          ${pythonEnv}/bin/ruff check . --fix --exit-zero --quiet || true
          echo "✅ Formatage terminé"
        '';
        
        smartTest = pkgs.writeShellScriptBin "smart-test" ''
          #!/usr/bin/env bash
          ${autoFormat}/bin/auto-format
          ${pythonEnv}/bin/pytest tests/ -v "$@"
        '';
        
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.git
            pkgs.just
            pkgs.pre-commit
            checkIntegrity
            setupVenv
            autoFormat
            smartTest
            pkgs.python3Packages.python-dotenv
          ];
          
          shellHook = ''
            echo "🌟 mif-dqf - Environnement activé"
            export PYTHONPATH="''${PYTHONPATH:-}:$(pwd)"
            
            check-integrity || echo "⚠️  Problèmes détectés"
            
            #[ ! -d ".venv" ] && setup-venv
            
            echo ""
            echo "📋 Commandes: check-integrity, setup-venv, auto-format, smart-test, just"
          '';
        };
      }
    );
}
