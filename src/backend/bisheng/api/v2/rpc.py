import json
from typing import Optional

from bisheng.database.base import get_session
from bisheng.database.models.user import User
from bisheng.database.models.user_role import UserRole
from bisheng.settings import settings
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi_jwt_auth import AuthJWT
from loguru import logger
from sqlmodel import Session, select

# build router
router = APIRouter(prefix='/rpc')


@router.get('/auth')
def set_cookie(*,
               deptId: Optional[str] = None,
               deptName: Optional[str] = None,
               menu: Optional[str] = '',
               user_id: Optional[int] = None,
               role_id: Optional[int] = None,
               session: Session = Depends(get_session),
               Authorize: AuthJWT = Depends()):
    """设置默认"""

    # admin
    try:
        if deptId:
            # this interface should update user model, and now the main ref don't mathes
            db_user = session.exec(select(User).where(User.dept_id == deptId)).first()
            if not db_user:
                db_user = User(user_name=deptName, password='none', dept_id=deptId)
                session.add(db_user)
                session.flush()
                db_user_role = UserRole(user_id=db_user.user_id, role_id=2)
                session.add(db_user_role)
                session.commit()
                session.refresh(db_user)
        else:
            raise ValueError('deptId 必须传递')
        payload = {'user_name': deptName, 'user_id': db_user.user_id, 'role': [2]}
        if role_id == 1:
            admin_user = session.query(User).where(User.user_name == 'root').first()
            if not admin_user:
                admin_user = User(user_name='root', password='none')
                session.add(admin_user)
                session.flush()
                session.refresh(admin_user)
                db_user_role = UserRole(user_id=admin_user.user_id, role_id=1)
                session.add(db_user_role)
            payload = {'user_name': 'root', 'user_id': admin_user.user_id, 'role': 'admin'}
            session.commit()
    except Exception as e:
        logger.error(str(e))
        session.rollback()
        return HTTPException(status_code=500, detail=str(e))

    # Create the tokens and passing to set_access_cookies or set_refresh_cookies
    access_token = Authorize.create_access_token(subject=json.dumps(payload), expires_time=864000)

    return RedirectResponse(
        settings.get_from_db('default_operator').get('url') + '/' + menu +
        f'?token={access_token}')
