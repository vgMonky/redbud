# default.nix
{ pkgs ? import <nixpkgs> {} }:

let
  python = pkgs.python310;
  pythonEnv = python.withPackages (ps: with ps; [
    requests 
    pytelegrambotapi 
    python-dotenv    
    openai          
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

