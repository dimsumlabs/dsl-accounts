with (import <nixpkgs> {});

mkShell {
  buildInputs = [ python3 ];
}
