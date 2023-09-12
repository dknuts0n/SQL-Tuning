# Time: 2023-09-08T21:34:59.028066Z
# User@Host: npvr[npvr] @  [10.7.14.234]  Id: 3896179
# Query_time: 2.356663  Lock_time: 0.000175 Rows_sent: 10  Rows_examined: 3801208
#  SET timestamp=1694208899;
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
	UNSR.userid = 1069015
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