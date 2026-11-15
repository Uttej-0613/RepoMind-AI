"""RepoMind command-line interface."""
import argparse
import json
from .core import answer, index_repository

def main():
    parser = argparse.ArgumentParser(description="Explore a local Python codebase")
    parser.add_argument("path", help="Directory to analyze")
    parser.add_argument("--ask", help="Question about the codebase")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    result = answer(args.path, args.ask, args.limit) if args.ask else {"symbols": [chunk.as_dict() for chunk in index_repository(args.path)]}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
