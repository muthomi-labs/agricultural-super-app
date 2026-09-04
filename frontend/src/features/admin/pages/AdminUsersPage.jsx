import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Badge, Button, ErrorState, Input, LoadingState, Modal, PageHeader } from '@/components/ui'
import { formatDate } from '@/lib/format'
import { errorMessage, useAuth } from '@/features/auth/AuthContext'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { fetchAdminUsers, updateAdminUser } from '@/store/slices/adminSlice'
import '../admin.css'

const ROLES = ['farmer', 'expert', 'admin']

export function AdminUsersPage() {
  const { t } = useTranslation('admin')
  const dispatch = useAppDispatch()
  const { user: currentAdmin } = useAuth()
  const users = useAppSelector((state) => state.admin.users)
  const status = useAppSelector((state) => state.admin.usersStatus)
  const error = useAppSelector((state) => state.admin.usersError)
  const total = useAppSelector((state) => state.admin.usersTotal)
  const page = useAppSelector((state) => state.admin.usersPage)
  const perPage = useAppSelector((state) => state.admin.usersPerPage)
  const updateLoadingId = useAppSelector((state) => state.admin.updateLoadingId)

  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [confirmAction, setConfirmAction] = useState(null) // { user, type: 'deactivate'|'activate'|'role', role? }
  const [actionError, setActionError] = useState(null)

  function load(nextPage = 1) {
    dispatch(fetchAdminUsers({ search: search.trim() || undefined, role: role || undefined, status: statusFilter || undefined, page: nextPage, perPage }))
  }

  useEffect(() => {
    load(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch])

  function handleFilterSubmit(event) {
    event.preventDefault()
    load(1)
  }

  async function confirmAndRun() {
    if (!confirmAction) return
    setActionError(null)
    try {
      if (confirmAction.type === 'deactivate') {
        await dispatch(updateAdminUser({ userId: confirmAction.user.user.id, isActive: false })).unwrap()
      } else if (confirmAction.type === 'activate') {
        await dispatch(updateAdminUser({ userId: confirmAction.user.user.id, isActive: true })).unwrap()
      } else if (confirmAction.type === 'role') {
        await dispatch(updateAdminUser({ userId: confirmAction.user.user.id, role: confirmAction.role })).unwrap()
      }
      setConfirmAction(null)
    } catch (err) {
      setActionError(errorMessage(err))
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / perPage))

  return (
    <>
      <PageHeader title={t('users.title')} subtitle={t('users.subtitle', { count: total })} />

      <form className="asa-admin-toolbar" onSubmit={handleFilterSubmit}>
        <Input
          label=""
          name="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('users.searchPlaceholder')}
          aria-label={t('users.searchAriaLabel')}
        />
        <select
          className="asa-input"
          style={{ width: 'auto' }}
          value={role}
          onChange={(e) => setRole(e.target.value)}
          aria-label={t('users.filterByRole')}
        >
          <option value="">{t('users.allRoles')}</option>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {t(`common:roles.${r}`)}
            </option>
          ))}
        </select>
        <select
          className="asa-input"
          style={{ width: 'auto' }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label={t('users.filterByStatus')}
        >
          <option value="">{t('users.allStatuses')}</option>
          <option value="active">{t('users.active')}</option>
          <option value="inactive">{t('users.deactivated')}</option>
        </select>
        <Button type="submit" variant="secondary">
          {t('users.filter')}
        </Button>
      </form>

      {status === 'loading' && <LoadingState label={t('users.loading')} />}
      {status === 'error' && <ErrorState message={error ?? undefined} onRetry={() => load(page)} />}

      {status === 'ready' && (
        <>
          <div className="asa-admin-table-wrap">
            <table className="asa-admin-table">
              <thead>
                <tr>
                  <th>{t('users.columnUsername')}</th>
                  <th>{t('users.columnEmail')}</th>
                  <th>{t('users.columnRole')}</th>
                  <th>{t('users.columnStatus')}</th>
                  <th>{t('users.columnJoined')}</th>
                  <th>{t('users.columnActions')}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isSelf = u.user.id === currentAdmin?.user.id
                  return (
                    <tr key={u.user.id}>
                      <td>
                        {u.user.username}
                        {isSelf && <span className="asa-admin-list-row__meta"> {t('users.you')}</span>}
                      </td>
                      <td>{u.user.email}</td>
                      <td>
                        <Badge variant={u.user.role === 'admin' ? 'success' : 'default'}>
                          {t(`common:roles.${u.user.role}`)}
                        </Badge>
                      </td>
                      <td>
                        <Badge variant={u.user.isActive ? 'success' : 'danger'}>
                          {u.user.isActive ? t('users.active') : t('users.deactivated')}
                        </Badge>
                      </td>
                      <td>{formatDate(u.user.createdAt)}</td>
                      <td>
                        {isSelf ? (
                          <span className="asa-admin-list-row__meta">{t('users.manageOwnAccount')}</span>
                        ) : (
                          <div className="asa-admin-table__actions">
                            <select
                              className="asa-input"
                              style={{ width: 'auto', minHeight: '2.25rem' }}
                              value={u.user.role}
                              onChange={(e) => setConfirmAction({ user: u, type: 'role', role: e.target.value })}
                              aria-label={t('users.changeRoleFor', { name: u.user.username })}
                            >
                              {ROLES.map((r) => (
                                <option key={r} value={r}>
                                  {t(`common:roles.${r}`)}
                                </option>
                              ))}
                            </select>
                            {u.user.isActive ? (
                              <Button
                                variant="danger"
                                size="sm"
                                loading={updateLoadingId === u.user.id}
                                onClick={() => setConfirmAction({ user: u, type: 'deactivate' })}
                              >
                                {t('users.deactivate')}
                              </Button>
                            ) : (
                              <Button
                                variant="secondary"
                                size="sm"
                                loading={updateLoadingId === u.user.id}
                                onClick={() => setConfirmAction({ user: u, type: 'activate' })}
                              >
                                {t('users.reactivate')}
                              </Button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="asa-admin-pagination">
            <span>{t('users.page', { page, totalPages })}</span>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => load(page - 1)}>
                {t('users.previous')}
              </Button>
              <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => load(page + 1)}>
                {t('users.next')}
              </Button>
            </div>
          </div>
        </>
      )}

      <Modal
        open={!!confirmAction}
        title={
          confirmAction?.type === 'deactivate'
            ? t('users.deactivateTitle')
            : confirmAction?.type === 'activate'
              ? t('users.reactivateTitle')
              : t('users.changeRoleTitle')
        }
        onClose={() => {
          setConfirmAction(null)
          setActionError(null)
        }}
      >
        {confirmAction?.type === 'deactivate' && (
          <p>{t('users.deactivateBody', { name: confirmAction.user.user.username })}</p>
        )}
        {confirmAction?.type === 'activate' && (
          <p>{t('users.reactivateBody', { name: confirmAction.user.user.username })}</p>
        )}
        {confirmAction?.type === 'role' && (
          <p>
            {t('users.changeRoleBody', {
              name: confirmAction.user.user.username,
              from: t(`common:roles.${confirmAction.user.user.role}`),
              to: t(`common:roles.${confirmAction.role}`),
            })}
          </p>
        )}
        {actionError && (
          <p className="asa-form-error" role="alert">
            {actionError}
          </p>
        )}
        <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
          <Button
            variant={confirmAction?.type === 'deactivate' ? 'danger' : 'primary'}
            loading={!!updateLoadingId}
            onClick={confirmAndRun}
          >
            {t('users.confirm')}
          </Button>
          <Button variant="ghost" onClick={() => setConfirmAction(null)}>
            {t('users.cancel')}
          </Button>
        </div>
      </Modal>
    </>
  )
}
