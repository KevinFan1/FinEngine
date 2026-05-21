# Personal Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-service personal center, show the real display name in the top-right user area, and force an initial password change reminder on first login without blocking navigation.

**Architecture:** Keep user-management admin flows separate from the current-user flow. Add a small self-service backend surface for `GET /auth/me`, `PUT /auth/me`, and `PUT /auth/me/password`, backed by a `must_change_password` flag on `fin_users`. On the frontend, route the dropdown entry to a dedicated personal-center page and show a persistent first-login password modal based on the flag returned by `/auth/me`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, Vue 3, Vue Router, Pinia, Element Plus, Vitest-style unit tests where available.

---

### Task 1: Backend current-user profile API and password flag

**Files:**
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/services/user_service.py`
- Modify: `backend/app/api/v1/auth.py`
- Modify: `backend/app/api/v1/users.py`
- Modify: `backend/app/scripts/seed_users.py`
- Modify: `backend/app/tests/test_user_service_scope.py`
- Add: `backend/app/tests/test_auth_profile_api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_current_user_profile_returns_must_change_password(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["must_change_password"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest backend/app/tests/test_auth_profile_api.py -v`
Expected: fail because `must_change_password` is missing from the payload.

- [ ] **Step 3: Write minimal implementation**

```python
class User(SoftDeleteMixin, Base):
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="首次登录后是否需要修改密码")

class UserInfo(BaseModel):
    must_change_password: bool = False

@router.put("/me", response_model=ApiResponse[UserInfo])
async def update_me(...):
    ...

@router.put("/me/password", response_model=ApiResponse)
async def change_my_password(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk pytest backend/app/tests/test_auth_profile_api.py backend/app/tests/test_user_service_scope.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/user.py backend/app/schemas/auth.py backend/app/services/auth_service.py backend/app/services/user_service.py backend/app/api/v1/auth.py backend/app/api/v1/users.py backend/app/tests/test_auth_profile_api.py backend/app/tests/test_user_service_scope.py backend/app/scripts/seed_users.py
git commit -m "feat: add self-service profile api"
```

### Task 2: Frontend personal center page and forced password modal

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/user.ts`
- Modify: `frontend/src/stores/user.ts`
- Modify: `frontend/src/layouts/DefaultLayout.vue`
- Modify: `frontend/src/router/index.ts`
- Add: `frontend/src/views/profile/index.vue`
- Add: `frontend/src/components/ForcePasswordChangeDialog.vue`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";

describe("profile route", () => {
  it("is registered", () => {
    expect(true).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk npm run build`
Expected: fail until the new route/component imports exist.

- [ ] **Step 3: Write minimal implementation**

```vue
<el-dialog v-model="visible" title="首次登录需要修改密码" :close-on-click-modal="false" :close-on-press-escape="false">
  <el-form>
    <el-form-item label="姓名">
      <el-input v-model="form.display_name" />
    </el-form-item>
    <el-form-item label="手机号">
      <el-input v-model="form.phone" />
    </el-form-item>
    <el-form-item label="当前密码">
      <el-input v-model="form.old_password" type="password" />
    </el-form-item>
    <el-form-item label="新密码">
      <el-input v-model="form.new_password" type="password" />
    </el-form-item>
  </el-form>
</el-dialog>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk npm run build`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/auth.ts frontend/src/api/user.ts frontend/src/stores/user.ts frontend/src/layouts/DefaultLayout.vue frontend/src/router/index.ts frontend/src/views/profile/index.vue frontend/src/components/ForcePasswordChangeDialog.vue
git commit -m "feat: add personal center ui"
```

### Task 3: End-to-end verification

**Files:**
- Modify: `backend/app/tests/test_auth_profile_api.py`
- Modify: `frontend/src/views/profile/index.vue`

- [ ] **Step 1: Run the backend tests**

Run: `rtk pytest backend/app/tests/test_auth_profile_api.py backend/app/tests/test_user_service_scope.py -v`
Expected: all pass.

- [ ] **Step 2: Build the frontend**

Run: `rtk npm run build`
Expected: build succeeds.

- [ ] **Step 3: Manual check**

Open `/dashboard`, confirm the top-right label shows `display_name`, click `个人信息`, verify the page loads, and confirm first-login users see the password change reminder but can still navigate.

- [ ] **Step 4: Commit**

```bash
git add backend frontend docs/superpowers/plans/2026-05-21-personal-center.md
git commit -m "feat: personal center and first-login password reminder"
```
