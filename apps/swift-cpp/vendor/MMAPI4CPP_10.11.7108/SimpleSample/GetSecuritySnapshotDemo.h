#pragma once
#include "FTAPIDemoBase.h"

class GetSecuritySnapshotDemo: public FTAPIDemoBase
{
public:
	GetSecuritySnapshotDemo();
	~GetSecuritySnapshotDemo();

	void Run();

private:
	void GetHKEqtySecList();
	void GetHKEqtySecQot();
	void ParseHKEqtySecQot();

private:
	vector<Qot_Common::Security> m_vHKEqtySecList;
	vector<Qot_GetSecuritySnapshot::Snapshot> m_vHKEqtySecQot;

protected:
	void OnReply_GetStaticInfo(Moomoo::u32_t nSerialNo, const Qot_GetStaticInfo::Response &stRsp);
	void OnReply_GetSecuritySnapshot(Moomoo::u32_t nSerialNo, const Qot_GetSecuritySnapshot::Response &stRsp);
};