import { describe, expect, it } from "vitest";
import { scoreQuiz, ankiTSV } from "./study";

describe("quiz scoring", () => {
  it("scores chosen options in application code, including unanswered questions", () => {
    expect(scoreQuiz([1, 0, undefined, 3, 2], [1, 2, 0, 3, 2])).toEqual({
      correct: 3,
      total: 5,
    });
  });
  it("rejects invalid answer keys", () => {
    expect(() => scoreQuiz([0], [4])).toThrow();
  });
});
describe("Anki export", () => {
  it("keeps tabs, newlines, quotes and unicode inside their original fields", () => {
    expect(
      ankiTSV([
        {
          question: 'What is "λ"?\tExplain',
          answer: "A function\nexpression",
          source: "Lecture 1, p. 2",
        },
      ]),
    ).toBe(
      '"What is ""λ""?\tExplain"\t"A function\nexpression"\t"Lecture 1, p. 2"\r\n',
    );
  });
});
