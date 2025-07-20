# default.nix
{ pkgs ? import <nixpkgs> {} }:

let
  python = pkgs.python311;
  pythonEnv = python.withPackages (ps: with ps; [
    requests 
    pytelegrambotapi 
    python-dotenv    
    openai     
    PyGithub
  ]);
in

pkgs.mkShell {
  name = "telegram-deepseek-bot-shell";
  buildInputs = [ pythonEnv ];
  shellHook = ''
    echo "🐍 Python environment ready → $(python -V)"
    export PYTHONUNBUFFERED=1
  '';
}

