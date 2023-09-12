# Time: 2023-09-06T21:45:52
# User@Host: npvr[npvr] @ 172.18.96.97:23527 []
# Query_time: 4.410214  Lock_time: 0.000000  Rows_sent: 0  Rows_examined: 0
use npvrbe;

select
	unsr.SERIESID,
	snsr.title,
	unsr.EPISODESCOPE,
	unsr.CHANNELBOUND,
	N.CHANNELEXTERNALID,
	unsr.DELETEWHENSPACENEEDED,
	unsr.EPISODESTOKEEP,
	snsr.SERIESREFNO,
	PD.uaseriesId,
	PD.uagrouptype,
	unsr.USERNAME,
	CH.CHANNELID
from
	SYSTEMNPVRSERIESRECORDING snsr,
	PROGRAMDETAILS PD,
	CHANNEL CH,
	USERNPVRSERIESRECORDING unsr,
	USERNPVRRECORDING U,
	NPVRASSET N
where
	UNSR.userid = 1949590
	and (unsr.CHANNELID = CH.CHANNELID
		or CH.CHANNELID is null)
	and N.CHANNELEXTERNALID = CH.CHANNELEXTERNALID
	and U.SERIESID = unsr.SERIESID
	and U.SERIESID is not null
	and unsr.USERID = U.USERID
	and snsr.SERIESREFNO = PD.SERIESREFERENCE
	and snsr.SERIESID = unsr.SERIESID
	and N.RECORDID = U.RECORDID
	and snsr.CONTEXTID = PD.CONTEXTID
	and PD.uaseriesId is not null
	and unsr.MARKEDFORDELETE = 0
group by
	snsr.SERIESREFNO ,
	N.CHANNELEXTERNALID;
	
