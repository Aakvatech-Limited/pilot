/**
 * Options for a pick-or-type branch Combobox: one selectable row per known
 * branch, the current selection prepended when it is not in the list (a
 * button-trigger Combobox shows its placeholder for values without a matching
 * option), and a `typed-branch` custom row that commits the typed query via
 * `onPick`. Render the row with an `#item-typed-branch` slot.
 */
export function branchComboboxOptions(branchNames, selected, onPick) {
  const options = branchNames.map((name) => ({ label: name, value: name }))
  if (selected && !branchNames.includes(selected)) {
    options.unshift({ label: selected, value: selected })
  }
  return [
    ...options,
    {
      type: 'custom',
      key: 'typed-branch',
      label: 'Use typed branch',
      slot: 'typed-branch',
      condition: ({ query }) => {
        const typed = query.trim()
        return Boolean(typed) && !options.some((option) => option.value === typed)
      },
      onClick: ({ query }) => {
        const typed = query.trim()
        if (typed) onPick(typed)
      },
    },
  ]
}
