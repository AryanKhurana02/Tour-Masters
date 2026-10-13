import { describe, expect, it } from "vitest";

import App from "./App";

describe("frontend scaffold", () => {
  it("exports the application entry point without rendering UI yet", () => {
    expect(App).toBeTypeOf("function");
  });
});
