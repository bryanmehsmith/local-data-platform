import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "./ErrorBoundary";

function Bomb(): never {
  throw new Error("boom");
}

describe("ErrorBoundary", () => {
  it("renders children normally when no error occurs", () => {
    render(
      <ErrorBoundary>
        <p>All good</p>
      </ErrorBoundary>,
    );

    expect(screen.getByText("All good")).toBeInTheDocument();
  });

  it("shows the fallback UI when a child throws during render", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    // jsdom reports uncaught render errors to stderr via window.reportError /
    // the "error" event, independent of console.error — silence that too so
    // this expected error doesn't spam test output.
    const onError = (event: ErrorEvent) => event.preventDefault();
    window.addEventListener("error", onError);

    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong.")).toBeInTheDocument();

    window.removeEventListener("error", onError);
    consoleErrorSpy.mockRestore();
  });
});
