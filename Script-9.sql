select npvrbe.unsr.SERIESID AS SERIESID,npvrbe.snsr.TITLE AS title,npvrbe.unsr.EPISODESCOPE AS EPISODESCOPE,
npvrbe.unsr.CHANNELBOUND AS CHANNELBOUND,npvrbe.n.CHANNELEXTERNALID AS CHANNELEXTERNALID,npvrbe.unsr.DELETEWHENSPACENEEDED AS DELETEWHENSPACENEEDED,
npvrbe.unsr.EPISODESTOKEEP AS EPISODESTOKEEP,npvrbe.snsr.SERIESREFNO AS SERIESREFNO,npvrbe.pd.uaseriesId AS uaseriesId,npvrbe.pd.uagrouptype AS uagrouptype,
npvrbe.unsr.USERNAME AS USERNAME,npvrbe.ch.CHANNELID AS CHANNELID from npvrbe.systemnpvrseriesrecording snsr join npvrbe.programdetails pd 
join npvrbe.channel ch 
join npvrbe.usernpvrseriesrecording unsr 
join npvrbe.usernpvrrecording u 
join npvrbe.npvrasset n 
	where ((npvrbe.unsr.MARKEDFORDELETE = 0) 
			and (npvrbe.pd.CONTEXTID = npvrbe.snsr.CONTEXTID) 
			and (npvrbe.n.RECORDID = npvrbe.u.RECORDID) 
			and (npvrbe.pd.SERIESREFERENCE = npvrbe.snsr.SERIESREFNO) 
			and (npvrbe.unsr.SERIESID = npvrbe.u.SERIESID) 
			and (npvrbe.snsr.SERIESID = npvrbe.u.SERIESID) 
			and (npvrbe.n.CHANNELEXTERNALID = npvrbe.ch.CHANNELEXTERNALID) 
			and (npvrbe.u.USERID = 1069015) 
			and (npvrbe.unsr.USERID = 1069015) 
			and (npvrbe.ch.CHANNELID = npvrbe.unsr.CHANNELID) 
			and (npvrbe.u.SERIESID is not null) 
			and (npvrbe.pd.uaseriesId is not null)) 
group by npvrbe.snsr.SERIESREFNO,npvrbe.n.CHANNELEXTERNALID;