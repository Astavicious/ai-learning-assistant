export function scoreQuiz(answers: (number | undefined)[], key: number[]) {
  if (key.some((value) => !Number.isInteger(value) || value < 0 || value > 3))
    throw new Error("Invalid answer key");
  return {
    correct: key.filter((value, index) => answers[index] === value).length,
    total: key.length,
  };
}

export function ankiTSV(
  cards: { question: string; answer: string; source: string }[],
) {
  const quote = (text: string) => `"${text.replace(/"/g, '""')}"`;
  return (
    cards
      .map((card) =>
        [card.question, card.answer, card.source].map(quote).join("\t"),
      )
      .join("\r\n") + "\r\n"
  );
}

export function download(
  filename: string,
  content: string,
  type = "text/markdown;charset=utf-8",
) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
