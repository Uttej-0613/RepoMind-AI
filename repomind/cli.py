"""Local offline CLI; hosted LLM requires explicit environment configuration."""
import argparse
import json
from .core import Index
from .llm import LLMUnavailable, answer


def main() -> None:
    parser = argparse.ArgumentParser(description='Analyze authorized local Python, JS and TS codebases')
    parser.add_argument('path', help='Directory to index; no files are modified')
    parser.add_argument('--ask', help='Natural-language retrieval question')
    parser.add_argument('--limit', type=int, default=6)
    parser.add_argument('--llm', action='store_true', help='Send relevant code snippets to a configured external LLM')
    parser.add_argument('--graph', action='store_true', help='Print import map instead of search')
    args = parser.parse_args()
    index = Index(args.path)
    if args.graph:
        data = index.graph()
    elif args.ask and args.llm:
        try:
            data = answer(args.ask, index.search(args.ask, args.limit))
        except LLMUnavailable as exc:
            parser.error(str(exc))
    else:
        data = {'summary': index.summary(), 'results': index.search(args.ask, args.limit) if args.ask else []}
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
