{
  description = "rki protocols semantic search flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    # Used for shell.nix
    flake-compat = {
      url = github:edolstra/flake-compat;
      flake = false;
    };
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    ...
  } @ inputs: let
  in
    flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = import nixpkgs {inherit system; };
        pythonEnv = pkgs.python310.withPackages (ps: [
            ps.flask
            ps.flask-restful
            ps.flask-httpauth
            ps.flask-cors
            # ps.markdown
            # ps.pygments
            # ps.flask-sqlalchemy
            # ps.flask_migrate
            ps.gunicorn

            ps.numpy
            ps.openai
            ps.faiss
        ]);
      in rec {
        devShells.default = pkgs.mkShell {
          nativeBuildInputs = with pkgs; [
            bat
            gnused
            pythonEnv
          ];

          buildInputs = with pkgs; [
            # we need a version of bash capable of being interactive
            # as opposed to a bash just used for building this flake 
            # in non-interactive mode
            bashInteractive 
          ];

          shellHook = ''
            # once we set SHELL to point to the interactive bash, neovim will 
            # launch the correct $SHELL in its :terminal 
            export SHELL=${pkgs.bashInteractive}/bin/bash
            export FLASK_APP=web.py
          '';
        };

        # For compatibility with older versions of the `nix` binary
        devShell = self.devShells.${system}.default;

        # packages
        packages.rkisearch = pkgs.stdenv.mkDerivation rec {
          name = "rkisearch";
          buildInputs = with pkgs; [
            pythonEnv
            bashInteractive
          ];

          script = pkgs.writeShellScript "rki-run" ''
            #!/usr/bin/env bash
            export HOME=/tmp
            export PYTHONPATH=${pythonEnv}/${pythonEnv.sitePackages}

            CONFIG=`python confutil.py`
            echo "received config: $CONFIG"
            BIND=`echo "$CONFIG" | sed 's/;.*$//'`
            echo "received BIND: $BIND"
            LOGDIR=`echo "$CONFIG" | sed 's/.*;//'`
            echo "received LOGDIR: $LOGDIR"

            mkdir -p $LOGDIR
            ${pkgs.python3Packages.gunicorn}/bin/gunicorn web:app -b$BIND | tee -a $LOGDIR/rkisearch-gunicorn.log 2>> $LOGDIR/oms-gunicorn.err
          '';

          src = ./.;

          installPhase = ''
            mkdir -p $out/bin
            cp -r . $out/bin/
            cp ${script} $out/bin/rkisearch
          '';

        };
        defaultPackage = self.packages.${system}.rkisearch;

        # Usage:
        #    nix build .#docker
        #    docker load < result
        #    docker run -p5000:5000 rkisearch:lastest
        packages.docker = pkgs.dockerTools.buildImage {
          name = "rkisearch";       # give docker image a name
          tag = "latest";     # provide a tag
          created = "now";

          copyToRoot = pkgs.buildEnv {
            name = "image-root";
            paths = [ packages.rkisearch pythonEnv pkgs.gnused pkgs.coreutils];
            pathsToLink = [ "/bin" "/tmp" ];
          };

          config = {
            Cmd = [ "${packages.rkisearch}/bin/rkisearch" ];
            WorkingDir = "/bin";
            Volumes = { 
                "/tmp" = { }; 
                };
            ExposedPorts = {
              "5100/tcp" = {};
            };
          };
        };


    });
}
