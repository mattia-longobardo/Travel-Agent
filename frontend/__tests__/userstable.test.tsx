import { render, screen, fireEvent } from "@testing-library/react";
import { UsersTable } from "@/components/admin/UsersTable";

const users = [
  { id: 1, username: "admin", email: "a@x", is_admin: true, is_active: true, group_id: null },
  { id: 2, username: "bob", email: "b@x", is_admin: false, is_active: false, group_id: null },
];

test("renders rows and toggles selection + sort", () => {
  const onToggle = vi.fn(), onSort = vi.fn(), onRowClick = vi.fn();
  render(<UsersTable users={users} selected={new Set()} sort="username" order="asc"
    onToggle={onToggle} onTogglePage={() => {}} onSort={onSort} onRowClick={onRowClick} />);
  expect(screen.getByText("bob")).toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("Seleziona bob"));
  expect(onToggle).toHaveBeenCalledWith(2, false);
  fireEvent.click(screen.getByRole("button", { name: /username/i }));
  expect(onSort).toHaveBeenCalledWith("username");
});

test("clicking a row opens it", () => {
  const onRowClick = vi.fn();
  render(<UsersTable users={users} selected={new Set()} sort="username" order="asc"
    onToggle={() => {}} onTogglePage={() => {}} onSort={() => {}} onRowClick={onRowClick} />);
  fireEvent.click(screen.getByText("bob"));
  expect(onRowClick).toHaveBeenCalledWith(expect.objectContaining({ id: 2 }));
});
