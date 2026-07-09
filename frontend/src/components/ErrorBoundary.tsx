import { Component, ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

type Props = { children: ReactNode };
type State = { error: Error | null };

// Catches render-time exceptions anywhere in the tree below it so a bug in
// one page can't blank the entire app — without this, React unmounts the
// whole component tree on an uncaught render error.
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error("Unhandled render error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-slate-950">
          <div className="flex max-w-md flex-col items-center gap-4 rounded-md border border-red-200 bg-red-50 px-6 py-8 text-center dark:border-red-500/30 dark:bg-red-500/10">
            <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
            <div>
              <p className="text-sm font-medium text-red-700 dark:text-red-400">
                Something went wrong.
              </p>
              <p className="mt-1 text-xs text-red-600/80 dark:text-red-400/70">
                {this.state.error.message}
              </p>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
