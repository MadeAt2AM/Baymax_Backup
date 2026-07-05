---
name: template-notes-management
description: "Add persistent notes to expense templates that clone during monthly rollover and manual ledger item creation"
category: feature
tags: [templates, notes, rollover, ledger, crud, payntra]
---

# Template Notes Management Feature

## Requirement
Add a `notes` field to `expense_templates` that:
1. Can be edited on the Templates page (edit name, amount, notes)
2. Gets cloned into `ledger_items.notes` during:
   - Monthly rollover (when no prior month exists — fallback to templates)
   - Manual "Add to current month" from Templates page

## Database Migration
```sql
ALTER TABLE expense_templates ADD COLUMN notes TEXT DEFAULT NULL;
```

## Server Changes

### 1. `schemas/templates.ts`
- Add `notes` to `TemplateSchema` (string | null)
- Add `notes` to `TemplateCreateSchema` (optional, max 5000 chars)
- Add `notes` to `TemplatePatchSchema` (optional, nullable)

### 2. `services/templates.ts`
- `toTemplate()` — include `notes: r.notes`
- `createTemplate()` — insert `notes` (default null)
- `updateTemplate()` — allow `patch.notes` update
- `listTemplates()` — already returns all columns

### 3. `services/rollover.ts`
- In fallback template clone: include `notes` in INSERT
- Add `notes` to `TemplateRow` interface

### 4. `services/createLedgerItem.ts` (manual "Add to current month")
- When `templateId` provided, fetch template's `notes` and insert into `ledger_items.notes`

## Client Changes

### 1. `types.ts`
- Add `notes?: string | null` to `Template`, `TemplateCreate`, `TemplatePatch`

### 2. `TemplatesPage.tsx`
- Add "Edit" button per template row (opens modal)
- Modal: pre-fill name, amount, notes; PATCH on save
- Show notes preview in list (truncated, tooltip on hover)

## Testing
- Server: update `templates.test.ts` for notes CRUD
- Server: update `rollover.test.ts` to verify notes cloned
- Client: add unit test for edit modal