import { render, screen, fireEvent } from "@testing-library/react";
import { ChatRow } from "@/components/ChatRow";

const chat = { id: 1, title: "Mare", params_json: {}, owner_id: 1, permission: "owner", status: "active", chat_group_id: null };

test("active chat menu offers archive and trash", () => {
  const onTrash = vi.fn();
  render(<ChatRow chat={chat} active={false} groups={[]} onSelect={() => {}}
    onArchive={() => {}} onTrash={onTrash} onRestore={() => {}} onDeleteForever={() => {}}
    onShare={() => {}} onMove={() => {}} onRename={() => {}} />);
  fireEvent.click(screen.getByLabelText("Azioni chat"));
  fireEvent.click(screen.getByText("Sposta nel cestino"));
  expect(onTrash).toHaveBeenCalledWith(1);
});

test("active chat menu offers rename and calls onRename with the chat id", () => {
  const onRename = vi.fn();
  render(<ChatRow chat={chat} active={false} groups={[]} onSelect={() => {}}
    onArchive={() => {}} onTrash={() => {}} onRestore={() => {}} onDeleteForever={() => {}}
    onShare={() => {}} onMove={() => {}} onRename={onRename} />);
  fireEvent.click(screen.getByLabelText("Azioni chat"));
  fireEvent.click(screen.getByText("Rinomina"));
  expect(onRename).toHaveBeenCalledWith(1);
});

test("no groups hides the move-to-group option", () => {
  render(<ChatRow chat={chat} active={false} groups={[]} onSelect={() => {}}
    onArchive={() => {}} onTrash={() => {}} onRestore={() => {}} onDeleteForever={() => {}}
    onShare={() => {}} onMove={() => {}} onRename={() => {}} />);
  fireEvent.click(screen.getByLabelText("Azioni chat"));
  expect(screen.queryByText("Sposta nel gruppo")).not.toBeInTheDocument();
  expect(screen.queryByText("Senza gruppo")).not.toBeInTheDocument();
});

test("with groups shows the move-to-group option", () => {
  render(<ChatRow chat={chat} active={false} groups={[{ id: 5, name: "Estate" }]} onSelect={() => {}}
    onArchive={() => {}} onTrash={() => {}} onRestore={() => {}} onDeleteForever={() => {}}
    onShare={() => {}} onMove={() => {}} onRename={() => {}} />);
  fireEvent.click(screen.getByLabelText("Azioni chat"));
  expect(screen.getByText("Sposta nel gruppo")).toBeInTheDocument();
  expect(screen.getByText("Estate")).toBeInTheDocument();
});

test("trashed chat menu offers restore and delete forever", () => {
  const onDel = vi.fn();
  render(<ChatRow chat={{ ...chat, status: "trashed" }} active={false} groups={[]} onSelect={() => {}}
    onArchive={() => {}} onTrash={() => {}} onRestore={() => {}} onDeleteForever={onDel}
    onShare={() => {}} onMove={() => {}} onRename={() => {}} />);
  fireEvent.click(screen.getByLabelText("Azioni chat"));
  fireEvent.click(screen.getByText("Elimina definitivamente"));
  expect(onDel).toHaveBeenCalledWith(1);
});
