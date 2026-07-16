import { render, screen, fireEvent } from "@testing-library/react";
import { MobileDrawer } from "@/components/mobile/MobileDrawer";
import type { ChatActions } from "@/lib/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

const noop = () => {};
const actions: ChatActions = {
  onSelect: vi.fn(), onArchive: noop, onTrash: noop, onRestore: noop,
  onDeleteForever: noop, onShare: noop, onMove: noop, onRename: noop,
};

test("mostra le chat e i tab di vista, e crea un nuovo viaggio", () => {
  const onNew = vi.fn();
  const onClose = vi.fn();
  render(
    <MobileDrawer
      open onClose={onClose}
      user={{ id: 1, username: "mat", email: "m@x.it", is_admin: false } as never}
      chats={[{ id: 7, title: "Tokyo", chat_group_id: null, status: "active" } as never]}
      groups={[]} view="active" activeChatId={7} actions={actions}
      onNew={onNew} onView={vi.fn()} onEmptyTrash={noop}
    />,
  );
  expect(screen.getByText("Tokyo")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /nuovo viaggio/i }));
  expect(onNew).toHaveBeenCalled();
  expect(onClose).toHaveBeenCalled();
});

test("chiude il drawer dopo il cambio vista", () => {
  const onClose = vi.fn();
  const onView = vi.fn();
  render(
    <MobileDrawer
      open onClose={onClose} user={null} chats={[]} groups={[]} view="active"
      activeChatId={null} actions={actions} onNew={noop} onView={onView} onEmptyTrash={noop}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: /archivio/i }));
  expect(onView).toHaveBeenCalledWith("archived");
  expect(onClose).toHaveBeenCalled();
});
